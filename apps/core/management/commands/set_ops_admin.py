from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant or revoke ops_admin group membership for a user."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Target username")
        parser.add_argument(
            "--action",
            required=True,
            choices=["grant", "revoke"],
            help="grant: add to ops_admin group; revoke: remove from ops_admin group",
        )

    def handle(self, *args, **options):
        username = options["username"]
        action = options["action"]
        user_model = get_user_model()

        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist as exc:
            raise CommandError(f"user not found: {username}") from exc

        group, _ = Group.objects.get_or_create(name="ops_admin")

        if action == "grant":
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f"granted ops_admin to {username}"))
        else:
            user.groups.remove(group)
            self.stdout.write(self.style.SUCCESS(f"revoked ops_admin from {username}"))
