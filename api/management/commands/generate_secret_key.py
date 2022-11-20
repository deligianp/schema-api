from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = 'Auxiliary script for generating new Django secret keys for deployment purposes'

    def handle(self, *args, **options):
        secret_key = get_random_secret_key()
        print(secret_key)
