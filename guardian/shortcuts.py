"""Convenient shortcuts to manage or check object permissions."""

from collections import defaultdict
from functools import lru_cache, partial
from itertools import groupby
from typing import Any, Optional, Type, TypeVar, Union
import warnings

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import (
    AutoField,
    BigIntegerField,
    CharField,
    Count,
    ForeignKey,
    IntegerField,
    Manager,
    Model,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Q,
    QuerySet,
    SmallIntegerField,
    UUIDField,
)
from django.db.models.expressions import Value
from django.db.models.functions import Cast, Replace
from django.shortcuts import _get_queryset

from guardian.core import ObjectPermissionChecker
from guardian.ctypes import get_content_type
from guardian.exceptions import (
    MixedContentTypeError,
    MultipleIdentityAndObjectError,
    WrongAppError,
)
from guardian.utils import (
    get_anonymous_user,
    get_group_obj_perms_model,
    get_identity,
    get_user_obj_perms_model,
)


@lru_cache(None)
def _get_ct_cached(app_label: str, codename: str) -> ContentType:
    """Caches `ContentType` instances like its `QuerySet` does."""
    pass


# kwargs are required to be connected to a django signal
def clear_ct_cache(**kwargs) -> None:
    """Helper to clear cache of `_get_ct_cached`"""
    pass


def _get_first(t):
    """Allow sorting/grouping by pk by returning first in result tuple"""
    pass


def assign_perm(
    perm: Union[str, Permission],
    user_or_group: Any,
    obj: Optional[Model] = None,
) -> Union[str, Permission, None]:
    """Assigns permission to user/group and object pair.

    Parameters:
        perm (str | Permission): permission to assign for the given `obj`,
            in format: `app_label.codename` or `codename` or `Permission` instance.
            If `obj` is not given, must be in format `app_label.codename` or `Permission` instance.
        user_or_group (User | AnaonymousUser | Group | list | QuerySet):
            instance of `User`, `AnonymousUser`, `Group`,
            list of `User` or `Group`, or queryset of `User` or `Group`;
            passing any other object would raise a`guardian.exceptions.NotUserNorGroup` exception
        obj (Model | QuerySet): Django's `Model` instance or QuerySet or
            a list of Django `Model` instances or `None` if assigning global permission.
            *Default* is `None`.

    Example:
        ```shell
        >>> from django.contrib.sites.models import Site
        >>> from django.contrib.auth.models import User
        >>> from guardian.shortcuts import assign_perm
        >>> site = Site.objects.get_current()
        >>> user = User.objects.create(username='joe')
        >>> assign_perm("change_site", user, site)
        <UserObjectPermission: example.com | joe | change_site>
        >>> user.has_perm("change_site", site)
        True

        # or we can assign permission for group:

        >>> group = Group.objects.create(name='joe-group')
        >>> user.groups.add(group)
        >>> assign_perm("delete_site", group, site)
        <GroupObjectPermission: example.com | joe-group | delete_site>
        >>> user.has_perm("delete_site", site)
        True
        ```

    Note: Global permissions
        This function may also be used to assign standard, *global* permissions if
        `obj` parameter is omitted. Added Permission would be returned in that

        ```shell
        >>> assign_perm("sites.change_site", user)
        <Permission: sites | site | Can change site>
        ```

    """
    if isinstance(user_or_group, list) and not user_or_group:
        return None

    if isinstance(obj, list) and not obj:
        return None

    user, group = get_identity(user_or_group)
    # If obj is None we try to operate on global permissions
    if obj is None:
        if not isinstance(perm, Permission):
            try:
                app_label, codename = perm.split(".", 1)
            except ValueError:
                raise ValueError(
                    "For global permissions, first argument must be in format: 'app_label.codename' (is %r)" % perm
                )
            perm = Permission.objects.get(content_type__app_label=app_label, codename=codename)

        if user:
            user.user_permissions.add(perm)
            return perm
        if group:
            group.permissions.add(perm)
            return perm

    if not isinstance(perm, Permission):
        if "." in perm:
            app_label, perm = perm.split(".", 1)

    if isinstance(obj, (QuerySet, list)):
        if isinstance(user_or_group, (QuerySet, list)):
            raise MultipleIdentityAndObjectError("Only bulk operations on either users/groups OR objects supported")
        if user:
            model = get_user_obj_perms_model(obj[0] if isinstance(obj, list) else obj.model)
            return model.objects.bulk_assign_perm(perm, user, obj)
        if group:
            model = get_group_obj_perms_model(obj[0] if isinstance(obj, list) else obj.model)
            return model.objects.bulk_assign_perm(perm, group, obj)

    if isinstance(user_or_group, (QuerySet, list)):
        if user:
            model = get_user_obj_perms_model(obj)
            return model.objects.assign_perm_to_many(perm, user, obj, ignore_conflicts=True)
        if group:
            model = get_group_obj_perms_model(obj)
            return model.objects.assign_perm_to_many(perm, group, obj, ignore_conflicts=True)

    if user:
        model = get_user_obj_perms_model(obj)
        return model.objects.assign_perm(perm, user, obj)

    if group:
        model = get_group_obj_perms_model(obj)
        return model.objects.assign_perm(perm, group, obj)
    return None


def assign(perm, user_or_group, obj=None):
    """Depreciated function name left in for compatibility"""
    pass


def remove_perm(
    perm: Union[str, Permission],
    user_or_group: Any = None,
    obj: Union[Model, QuerySet, list, None] = None,
) -> Union[tuple[int, dict], None]:
    """Removes permission from user/group and object pair.

    Parameters:
        perm (str | Permission): permission to remove for the given `obj`, in format: `app_label.codename` or `codename` or `Permission` instance.
            If `obj` is not given, must be in format `app_label.codename` or `Permission` instance.
        user_or_group (User | AnonymousUser | Group | list | QuerySet):
            instance of `User`, `AnonymousUser`, `Group`,
            list of `User` or `Group`, or queryset of `User` or `Group`;
            passing any other object would raise a `guardian.exceptions.NotUserNorGroup` exception
        obj (Model | QuerySet | None): Django's `Model` instance or QuerySet or
            a list of Django `Model` instances or `None` if removing global permission.
            *Default* is `None`.
    """
    pass


def get_perms(user_or_group: Any, obj: Model) -> list[str]:
    """Get all permissions for given user/group and object pair.

    This function returns a comprehensive list of all permissions that the user or group
    has for the specified object. For users, this includes both direct permissions
    and permissions inherited from groups.

    Args:
        user_or_group: User, AnonymousUser, or Group instance
        obj: Django model instance for which to check permissions

    Returns:
        List of permission codenames (strings) for the given user/group and object pair.

    Note:
        For inactive users (is_active=False), returns empty list [].
        For superusers, returns all available permissions for the object's model.
    """
    check = ObjectPermissionChecker(user_or_group)
    return check.get_perms(obj)


def get_user_perms(user: Any, obj: Model) -> QuerySet:
    """Get permissions assigned DIRECTLY to a user for a specific object.

    This function returns ONLY permissions that are explicitly assigned to the user
    for the given object. It does NOT include permissions inherited from groups.

    Args:
        user: User or AnonymousUser instance
        obj: Django model instance for which to check permissions

    Returns:
        QuerySet of permission codenames (strings) that are directly assigned
        to the user for the given object.

    Note:
        For inactive users (is_active=False), returns empty QuerySet.
        Return type is QuerySet, not list (unlike get_perms()).
    """
    check = ObjectPermissionChecker(user)
    return check.get_user_perms(obj)


def get_group_perms(user_or_group: Any, obj: Model) -> QuerySet[Permission]:
    """Get permissions assigned to groups for a specific object.

    This function returns permissions that are assigned to groups for the given object.
    When called with a user, it returns permissions from ALL groups the user belongs to.
    When called with a group, it returns permissions for that specific group only.

    Args:
        user_or_group: User, AnonymousUser, or Group instance
        obj: Django model instance for which to check permissions

    Returns:
        QuerySet of permission codenames (strings) assigned to the group(s)
        for the given object.

    Note:
        For inactive users (is_active=False), returns empty QuerySet.
        Return type is QuerySet, not list (unlike get_perms()).
        Does NOT include direct user permissions.
    """
    check = ObjectPermissionChecker(user_or_group)
    return check.get_group_perms(obj)


def get_perms_for_model(cls: Union[Type[Model], Model, str]) -> QuerySet:
    """Get all permissions for a given model class.

    Returns:
        QuerySet of all Permission objects for the given class.
            It is possible to pass Model as class or instance.
    """
    pass


def get_users_with_perms(
    obj: Model,
    attach_perms: bool = False,
    with_superusers: bool = False,
    with_group_users: bool = True,
    only_with_perms_in: Optional[list[str]] = None,
) -> Union[Any, list[str]]:
    """Get all users with *any* object permissions for the given `obj`.

    Parameters:
        obj (Model): Instance of a Django `Model`.
        attach_perms (bool): If `True`, return a dictionary of `User` instances
            with the permissions' codename as a list of values.
            This fetches users eagerly!
        with_superusers (bool): Wether results should contain superusers.
        with_group_users (bool): Whether results should contain users who
            have only group permissions for given `obj`.
        only_with_perms_in (list[str]): Only return users with these permissions.
    Example:
        ```shell
        >>> from django.contrib.flatpages.models import FlatPage
        >>> from django.contrib.auth.models import User
        >>> from guardian.shortcuts import assign_perm, get_users_with_perms
        >>>
        >>> page = FlatPage.objects.create(title='Some page', path='/some/page/')
        >>> joe = User.objects.create_user('joe', 'joe@example.com', 'joesecret')
        >>> dan = User.objects.create_user('dan', 'dan@example.com', 'dansecret')
        >>> assign_perm('change_flatpage', joe, page)
        >>> assign_perm('delete_flatpage', dan, page)
        >>>
        >>> get_users_with_perms(page)
        [<User: joe>, <User: dan>]
        >>>
        >>> get_users_with_perms(page, attach_perms=True)
        {<User: joe>: [u'change_flatpage'], <User: dan>: [u'delete_flatpage']}
        >>> get_users_with_perms(page, only_with_perms_in=['change_flatpage'])
        [<User: joe>]
        ```
    """
    pass


def get_groups_with_perms(
    obj: Model, attach_perms: bool = False, only_with_perms_in: Optional[list[str]] = None
) -> Union[Group, dict]:
    """Get all groups with *any* object permissions for the given `obj`.

    Parameters:
        obj (Model): persisted Django `Model` instance.
        attach_perms (bool): Whether return result as a dict of `Group` instances
            with permissions' codenames list of values.
            This would fetch groups eagerly!
        only_with_perms_in (list[str]): Only return groups with these permissions.

    Returns:
        All `Group` objects with the matching object permissions for the given `obj`.

    Example:
        ```shell
        >>> from django.contrib.flatpages.models import FlatPage
        >>> from guardian.shortcuts import assign_perm, get_groups_with_perms
        >>> from guardian.models import Group
        >>>
        >>> page = FlatPage.objects.create(title='Some page', path='/some/page/')
        >>> admins = Group.objects.create(name='Admins')
        >>> assign_perm('change_flatpage', admins, page)
        >>>
        >>> get_groups_with_perms(page)
        [<Group: admins>]
        >>>
        >>> get_groups_with_perms(page, attach_perms=True)
        {<Group: admins>: [u'change_flatpage']}
        ```
    """
    pass


T = TypeVar("T", bound=Model)


def get_objects_for_user(
    user: Any,
    perms: Union[str, list[str]],
    klass: Union[Type[T], Manager[T], QuerySet[T], None] = None,
    use_groups: bool = True,
    any_perm: bool = False,
    with_superuser: bool = True,
    accept_global_perms: bool = True,
) -> QuerySet[T]:
    """Get objects that a user has *all* the supplied permissions for.

    Parameters:
        user (User | AnonymousUser): user to check for permissions.
        perms (str | list[str]): permission(s) to be checked.
            If `klass` parameter is not given, those should be full permission
            names rather than only codenames (i.e. `auth.change_user`).
            If more than one permission is present within sequence, their content type **must** be
            the same or `MixedContentTypeError` exception would be raised.
        klass (Modal | Manager | QuerySet): If not provided, this parameter would be
            computed based on given `params`.
        use_groups (bool): Whether to check user's groups object permissions.
        any_perm (bool): Whether any of the provided permissions in sequence is accepted.
        with_superuser (bool): if `user.is_superuser`, whether to return the entire queryset.
            Otherwise will only return objects the user has explicit permissions.
            This must be `True` for the `accept_global_perms` parameter to have any affect.
        accept_global_perms (bool): Whether global permissions are taken into account.
            Object based permissions are taken into account if more than one permission is
            provided in in perms and at least one of these perms is not globally set.
            If `any_perm` is `False` then the intersection of matching object is returned.
            Note, that if `with_superuser` is `False`, `accept_global_perms` will be ignored,
            which means that only object permissions will be checked!

    Raises:
        MixedContentTypeError: when computed content type for `perms` and/or `klass` clashes.
        WrongAppError: if cannot compute app label for given `perms` or `klass`.

    Example:
        ```shell
        >>> from django.contrib.auth.models import User
        >>> from guardian.shortcuts import get_objects_for_user
        >>> joe = User.objects.get(username='joe')
        >>> get_objects_for_user(joe, 'auth.change_group')
        []
        >>> from guardian.shortcuts import assign_perm
        >>> group = Group.objects.create('some group')
        >>> assign_perm('auth.change_group', joe, group)
        >>> get_objects_for_user(joe, 'auth.change_group')
        [<Group some group>]

        # The permission string can also be an iterable. Continuing with the previous example:

        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'])
        []
        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'], any_perm=True)
        [<Group some group>]
        >>> assign_perm('auth.delete_group', joe, group)
        >>> get_objects_for_user(joe, ['auth.change_group', 'auth.delete_group'])
        [<Group some group>]

        # Take global permissions into account:

        >>> jack = User.objects.get(username='jack')
        >>> assign_perm('auth.change_group', jack) # this will set a global permission
        >>> get_objects_for_user(jack, 'auth.change_group')
        [<Group some group>]
        >>> group2 = Group.objects.create('other group')
        >>> assign_perm('auth.delete_group', jack, group2)
        >>> get_objects_for_user(jack, ['auth.change_group', 'auth.delete_group']) # this retrieves intersection
        [<Group other group>]
        >>> get_objects_for_user(jack, ['auth.change_group', 'auth.delete_group'], any_perm) # this retrieves union
        [<Group some group>, <Group other group>]
        ```

    Note:
        If `accept_global_perms` is set to `True`, then all assigned global
        permissions will also be taken into account.

        - Scenario 1: a user has view permissions generally defined on the model
          'books' but no object-based permission on a single book instance:

            - If `accept_global_perms` is `True`: A list of all books will be returned.
            - If `accept_global_perms` is `False`: The list will be empty.

        - Scenario 2: a user has view permissions generally defined on the model
          'books' and also has an object-based permission to view book 'Whatever':

            - If `accept_global_perms` is `True`: A list of all books will be returned.
            - If `accept_global_perms` is `False`: The list will only contain book 'Whatever'.

        - Scenario 3: a user only has object-based permission on book 'Whatever':

            - If `accept_global_perms` is `True`: The list will only contain book 'Whatever'.
            - If `accept_global_perms` is `False`: The list will only contain book 'Whatever'.

        - Scenario 4: a user does not have any permission:

            - If `accept_global_perms` is `True`: An empty list is returned.
            - If `accept_global_perms` is `False`: An empty list is returned.

    Note: Primary key types
        Standard PK types (integer family, ``UUIDField``, ``CharField``) use
        optimised native casts. Non-standard PK types (e.g. ``TextField``,
        PostgreSQL ``macaddr``/``inet``) are automatically handled via a
        ``Cast("pk", CharField())`` fallback, so models with any PK type are
        supported without extra configuration.
    """
    pass


def get_objects_for_group(
    group: Group,
    perms: Union[str, list[str]],
    klass: Union[Model, Manager, QuerySet, None] = None,
    any_perm: bool = False,
    accept_global_perms: bool = True,
) -> QuerySet:
    """Get objects that a group has *all* the supplied permissions for.

    Parameters:
        group (Group): `Group` instance for which objects would be returned.
        perms (str | list[str]): permission(s) which should be checked.
            If `klass` parameter is not given, those should be full permission
            names rather than only codenames (i.e. `auth.change_user`).
            If more than one permission is present within sequence,
            their content type **must** be the same or `MixedContentTypeError` exception is raised.
        klass (Model | Manager | QuerySet):  If not provided this parameter is computed
            based on given `params`.
        any_perm (bool): Whether any of permission in sequence is accepted.
        accept_global_perms (bool): Whether global permissions are taken into account.
            If `any_perm` is `False`, then the intersection of matching objects based on
            global and object-based permissionsis returned.

    Returns:
        objects for which a given `group` has *all* permissions in `perms`.

    Raisess:
        MixedContentTypeError: when computed content type for `perms` and/or `klass` clashes.
        WrongAppError: if cannot compute app label for given `perms`/`klass`.

    Example:
        Let's assume we have a `Task` model belonging to the `tasker` app with
        the default add_task, change_task and delete_task permissions provided
        by Django:

        ```shell
        >>> from guardian.shortcuts import get_objects_for_group
        >>> from tasker import Task
        >>> group = Group.objects.create('some group')
        >>> task = Task.objects.create('some task')
        >>> get_objects_for_group(group, 'tasker.add_task')
        []
        >>> from guardian.shortcuts import assign_perm
        >>> assign_perm('tasker.add_task', group, task)
        >>> get_objects_for_group(group, 'tasker.add_task')
        [<Task some task>]

        # The permission string can also be an iterable. Continuing with the previous example:

        >>> get_objects_for_group(group, ['tasker.add_task', 'tasker.delete_task'])
        []
        >>> assign_perm('tasker.delete_task', group, task)
        >>> get_objects_for_group(group, ['tasker.add_task', 'tasker.delete_task'])
        [<Task some task>]

        # Global permissions assigned to the group are also taken into account. Continuing with previous example:

        >>> task_other = Task.objects.create('other task')
        >>> assign_perm('tasker.change_task', group)
        >>> get_objects_for_group(group, ['tasker.change_task'])
        [<Task some task>, <Task other task>]
        >>> get_objects_for_group(group, ['tasker.change_task'], accept_global_perms=False)
        [<Task some task>]
        ```

    Note: Primary key types
        Standard PK types (integer family, ``UUIDField``, ``CharField``) use
        optimised native casts. Non-standard PK types (e.g. ``TextField``,
        PostgreSQL ``macaddr``/``inet``) are automatically handled via a
        ``Cast("pk", CharField())`` fallback, so models with any PK type are
        supported without extra configuration.
    """
    pass


def _handle_pk_field(queryset):
    pass


def filter_perms_queryset_by_objects(perms_queryset, objects):
    pass
