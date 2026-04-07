from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate

from . import monkey_patch_group, monkey_patch_user


class GuardianConfig(AppConfig):
    name = "guardian"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        pass
