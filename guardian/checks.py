from django.conf import settings
from django.core.checks import Tags, Warning, register


# noinspection PyUnusedLocal
@register(Tags.compatibility)
def check_settings(app_configs, **kwargs):
    """Check that settings are implemented properly
    :param app_configs: a list of apps to be checks or None for all
    :param kwargs: keyword arguments
    :return: a list of errors
    """
    pass
