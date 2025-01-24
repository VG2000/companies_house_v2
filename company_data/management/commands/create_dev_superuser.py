from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create a development superuser using email instead of username'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = 'dev@example.com'
        username = 'dev_user'

        # Check if a user with the specified email already exists
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password='password',
                first_name='Dev',  # Optional: Add default values for other fields
                last_name='User',
                username=username
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created dev superuser with username: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Dev superuser with username {username} already exists'))
