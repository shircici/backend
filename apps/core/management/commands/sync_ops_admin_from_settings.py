from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync OPS_ADMIN_USERNAMES into ops_admin group."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying group membership.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        user_model = get_user_model()
        target_usernames = [u for u in getattr(settings, "OPS_ADMIN_USERNAMES", []) if u]
        group, _ = Group.objects.get_or_create(name="ops_admin")

        added = []
        missing = []
        already = []

        for username in target_usernames:
            user = user_model.objects.filter(username=username).first()
            if not user:
                missing.append(username)
                continue
            if group.user_set.filter(id=user.id).exists():
                already.append(username)
                continue
            added.append(username)
            if not dry_run:
                group.user_set.add(user)

        self.stdout.write(f"dry_run={dry_run}")
        self.stdout.write(f"added={len(added)} -> {added}")
        self.stdout.write(f"already_in_group={len(already)} -> {already}")
        self.stdout.write(f"missing_users={len(missing)} -> {missing}")
