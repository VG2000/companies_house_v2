from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Create a prod superuser using email instead of username'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = 'vgomez@jacksonsqpartners.com'
        username = 'vgomez'

        # Check if a user with the specified email already exists
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password='F/949482113565qp',
                first_name='Vince',  # Optional: Add default values for other fields
                last_name='Gomez',
                username=username
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created prod superuser with username: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Prod superuser with username {username} already exists'))
