from collections import OrderedDict
from typing import Type

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from guardian.forms import GroupObjectPermissionsForm, UserObjectPermissionsForm
from guardian.shortcuts import (
    get_group_perms,
    get_groups_with_perms,
    get_perms_for_model,
    get_user_perms,
    get_users_with_perms,
)
from guardian.utils import get_group_obj_perms_model


class GuardedInlineAdminMixin:
    """Mixin for Django admin inline classes to work with Guardian permissions.

    This mixin provides the necessary permission checking methods that Django's
    inline admin forms expect, integrating with Guardian's object-level permissions.

    Usage:
        class MyInline(GuardedInlineAdminMixin, admin.StackedInline):
            model = MyModel

        class MyAdmin(GuardedModelAdminMixin, admin.ModelAdmin):
            inlines = [MyInline]
    """

    def has_add_permission(self, request, obj=None):
        """Check if the user has permission to add instances of this inline model."""
        pass

    def has_view_permission(self, request, obj=None):
        """Check if the user has permission to view instances of this inline model."""
        pass

    def has_change_permission(self, request, obj=None):
        """Check if the user has permission to change instances of this inline model."""
        pass

    def has_delete_permission(self, request, obj=None):
        """Check if the user has permission to delete instances of this inline model."""
        pass


class AdminUserObjectPermissionsForm(UserObjectPermissionsForm):
    """Admin form for user object permissions.

    Extends the `UserObjectPermissionsForm` and overrides the
    `get_obj_perms_field_widget` method so it returns the
    `django.contrib.admin.widgets.FilteredSelectMultiple` widget.
    """

    def get_obj_perms_field_widget(self):
        pass


class AdminGroupObjectPermissionsForm(GroupObjectPermissionsForm):
    """Admin form for group object permissions.

    Extends the `GroupObjectPermissionsForm` and overrides the
    `get_obj_perms_field_widget` method so it returns the
    `django.contrib.admin.widgets.FilteredSelectMultiple` widget.
    """

    def get_obj_perms_field_widget(self):
        pass


class GuardedModelAdminMixin:
    """Mixin helper for custom subclassing `admin.ModelAdmin`."""

    change_form_template: str = "admin/guardian/model/change_form.html"
    obj_perms_manage_template: str = "admin/guardian/model/obj_perms_manage.html"
    obj_perms_manage_user_template: str = "admin/guardian/model/obj_perms_manage_user.html"
    obj_perms_manage_group_template: str = "admin/guardian/model/obj_perms_manage_group.html"
    user_can_access_owned_objects_only: bool = False
    user_owned_objects_field: str = "user"
    user_can_access_owned_by_group_objects_only: bool = False
    group_owned_objects_field: str = "group"
    include_object_permissions_urls: bool = True

    def get_queryset(self, request):
        pass

    def get_urls(self):
        """

        Extends standard admin model urls with the following:
        - `.../permissions/` under `app_mdodel_permissions` url name (params: object_pk)
        - `.../permissions/user-manage/<user_id>/` under `app_model_permissions_manage_user` url name (params: object_pk, user_pk)
        - `.../permissions/group-manage/<group_id>/` under `app_model_permissions_manage_group` url name (params: object_pk, group_pk)

        Note:
           `...` above are standard, instance detail url (i.e. `/admin/flatpages/1/`)

        """
        pass

    def get_obj_perms_base_context(self, request, obj):
        """Get context dict with common admin and object permissions related content.

        Returns context dictionary with common admin and object permissions
        related content. It uses AdminSite.each_context,
        making sure all required template vars are in the context.

        Returns:
            django template context
        """
        pass

    def obj_perms_manage_view(self, request, object_pk):
        """Main object permissions view.

        Presents all users and groups with any object permissions for the current model *instance*.
        Users or groups without object permissions for related *instance* would **not** be shown.
        To add or manage user or group, one should use links or forms presented within the page.
        """
        pass

    def get_obj_perms_manage_template(self):
        """
        Returns main object permissions admin template.  May be overridden if
        need to change it dynamically.

        Note:
           If `INSTALLED_APPS` contains `grappelli` this function would
           return `"admin/guardian/grappelli/obj_perms_manage.html"`.

        """
        pass

    def obj_perms_manage_user_view(self, request, object_pk, user_id):
        """Manages selected users' permissions for the current object."""
        pass

    def get_obj_perms_manage_user_template(self) -> str:
        """Returns object permissions for user admin template.

        May be overridden if dynamic behavior is needed.

        Note:
           If `INSTALLED_APPS` contains "grappelli" this function returns
           `"admin/guardian/grappelli/obj_perms_manage_user.html"`.
           Else, it returns `self.obj_perms_manage_user_template`.
        """
        pass

    def get_obj_perms_user_select_form(self, request: HttpRequest) -> Type[forms.Form]:
        """Get the form class for selecting a user for permissions management.

        Parameters:
            request (HttpRequest): The HTTP request object.

        Returns:
            The form class for selecting a user for permissions management.
                Default is `UserManage`
        """
        pass

    def get_obj_perms_group_select_form(self, request: HttpRequest) -> Type[forms.Form]:
        """Get the form class for group object permissions management.
        Parameters:
            request (HttpRequest): The HTTP request object.

        Returns:
            The form class for group object permissions management.
                Default is `GroupManage`
        """
        pass

    def get_obj_perms_manage_user_form(self, request: HttpRequest) -> Type[forms.Form]:
        """Get the form class for user object permissions management.

        Parameters:
            request (HttpRequest): The HTTP request object.

        Returns:
            The form class for user object permissions management.
                Default is `AdminUserObjectPermissionsForm`.
        """
        pass

    def obj_perms_manage_group_view(self, request, object_pk, group_id):
        """Manages selected groups' permissions for the current object."""
        pass

    def get_obj_perms_manage_group_template(self):
        """Returns object permissions for group admin template.

        May be overridden if dynamic behavior is needed.

        Returns:
            template name

        Note:
           If `INSTALLED_APPS` contains `grappelli` this function would
           return `"admin/guardian/grappelli/obj_perms_manage_group.html"`.
        """
        pass

    def get_obj_perms_manage_group_form(self, request):
        """Get the form class for group object permissions management.

        Parameters:
            request (HttpRequest): The HTTP request object.

        Returns:
            The form class for group object permissions management.
                Default is `AdminGroupObjectPermissionsForm`.
        """
        pass


class GuardedModelAdmin(GuardedModelAdminMixin, admin.ModelAdmin):
    """Provide views for managing object permissions on the Django admin panel.

    Extends the `django.contrib.admin.ModelAdmin` class.
    It uses `'admin/guardian/model/change_form.html'` as the
    default `change_form_template` attribute which is required for proper
    url (object permissions related) being shown at the model pages.

    Attributes:
        obj_perms_manage_template (str): Defaults to `admin/guardian/model/obj_perms_manage.html`
        obj_perms_manage_user_template (str): Defaults to `admin/guardian/model/obj_perms_manage_user.html`
        obj_perms_manage_group_template (str): Defaults to `admin/guardian/model/obj_perms_manage_group.html`
        user_can_access_owned_objects_only (bool): Defaults to `False`.
            If `True`, `request.user` would be used to filter out objects they don't own
            checking `user` field of used model -
            field name may be overridden by the `user_owned_objects_field` option.
        user_can_access_owned_by_group_objects_only (bool): *Default*: `False`
            If `True`, `request.user` is used to filter out objects her or his group doesn't own
            (checking if any group the user belongs to is set as `group` field of the object;
            name of the field can be changed by overriding `group_owned_objects_field`).
        group_owned_objects_field (str): *Default*: `group`
            Name of the field to check for group ownership.
        include_object_permissions_urls (bool): *Default*: `True`
            Added in version 1.2.
            If `False` guardian-specific URLs are **NOT** included in the admin

    Warning:
       Setting `user_can_access_owned_objects_only` to `True` will **NOT** affect superusers!
       Admins would still see all items.

    Warning:
       Setting `user_can_access_owned_by_group_objects_only` to `True` will **NOT** affect superusers!
       Admins would still see all items.


    Example:
        ```python
        # Just use GuardedModelAdmin instead of django.contrib.admin.ModelAdmin.

        from django.contrib import admin
        from guardian.admin import GuardedModelAdmin
        from myapp.models import Author

        class AuthorAdmin(GuardedModelAdmin):
            pass

        admin.site.register(Author, AuthorAdmin)
        ```
    """


class UserManage(forms.Form):
    user = forms.CharField(
        label=_("User identification"),
        max_length=200,
        error_messages={"does_not_exist": _("This user does not exist")},
        help_text=_("Enter a value compatible with User.USERNAME_FIELD"),
    )

    def clean_user(self):
        """Returns `User` instance based on the given identification."""
        pass


class GroupManage(forms.Form):
    group = forms.CharField(max_length=80, error_messages={"does_not_exist": _("This group does not exist")})

    def clean_group(self):
        """Returns `Group` instance based on the given group name."""
        pass
