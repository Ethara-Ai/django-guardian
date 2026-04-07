from django.contrib.auth import get_user_model
from django.db import DatabaseError, router
from django.db.models import signals
from django.utils.module_loading import import_string

from guardian.conf import settings as guardian_settings


def get_init_anonymous_user(User):
    """
    Returns User model instance that would be referenced by guardian when
    permissions are checked against users that haven't signed into the system.

    :param User: User model - result of ``django.contrib.auth.get_user_model``.
    """
    pass


def create_anonymous_user(sender, **kwargs):
    """
    Creates anonymous User instance with id and username from settings.
    """
    pass


# Only create an anonymous user if support is enabled.
if guardian_settings.ANONYMOUS_USER_NAME is not None:
    from django.apps import apps

    guardian_app = apps.get_app_config("guardian")
    signals.post_migrate.connect(
        create_anonymous_user, sender=guardian_app, dispatch_uid="guardian.management.create_anonymous_user"
    )
