from django.core.management.base import BaseCommand

from guardian.utils import clean_orphan_obj_perms


class Command(BaseCommand):
    """A wrapper around `guardian.utils.clean_orphan_obj_perms`.

    Seeks and removes all object permissions entries pointing at non-existing targets.
    Returns the number of objects removed.

    Example:
        ```shell
        $ python manage.py clean_orphan_obj_perms
        Removed 11 object permission entries with no targets

        $ python manage.py clean_orphan_obj_perms --batch-size 100 --max-batches 5
        Removed 500 object permission entries with no targets

        $ python manage.py clean_orphan_obj_perms --batch-size 50 --skip-batches 2 --max-duration-secs 60
        Removed 200 object permission entries with no targets
        ```
    """

    help = "Removes object permissions with not existing targets"

    def add_arguments(self, parser):
        pass

    def handle(self, **options):
        pass
