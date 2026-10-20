import os
import time

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import connection, transaction, OperationalError


class Command(BaseCommand):
    help = "Create the initial Django superuser once."

    def handle(self, *args, **options):
        email = os.environ.get("INITIAL_ADMIN_EMAIL")
        password = os.environ.get("INITIAL_ADMIN_PASSWORD")

        if not email or not password:
            raise CommandError(
                "Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD."
            )

        User = get_user_model()
        username_field = User.USERNAME_FIELD

        for attempt in range(1, 6):
            try:
                with transaction.atomic():
                    user = User._default_manager.filter(
                        **{username_field: email}
                    ).first()

                    if user:
                        if user.is_superuser:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    "Superuser already exists. Nothing changed."
                                )
                            )
                            return

                        raise CommandError(
                            "This account exists but is not a superuser. "
                            "No changes were made."
                        )

                    User._default_manager.create_superuser(
                        **{username_field: email},
                        password=password,
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Superuser {email} created successfully."
                    )
                )
                return

            except OperationalError:
                connection.close()

                if attempt == 5:
                    raise

                self.stdout.write(
                    f"Database connection failed, retrying "
                    f"({attempt}/5)..."
                )
                time.sleep(3)