from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):

        self.stdout.write("Creating 10 test users")
        for i in range(1, 11):
            username = "test_{}".format(i)
            email="test{}@test.com".format(i)
            User.objects.get_or_create(username=username,
                                       email=email,
                                       password="test")
