from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Remove ops_admin group users that are not in OPS_ADMIN_USERNAMES."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview removals without modifying group membership.",
        )
        parser.add_argument(
            "--keep-superuser",
            action="store_true",
            help="Do not remove superusers from ops_admin group.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        keep_superuser = options["keep_superuser"]
        whitelist = set([u for u in getattr(settings, "OPS_ADMIN_USERNAMES", []) if u])

        group = Group.objects.filter(name="ops_admin").first()
        if not group:
            self.stdout.write("ops_admin group not found, nothing to prune.")
            return

        removed = []
        kept = []

        for user in group.user_set.all():
            if user.username in whitelist:
                kept.append(user.username)
                continue
            if keep_superuser and user.is_superuser:
                kept.append(user.username)
                continue
            removed.append(user.username)
            if not dry_run:
                group.user_set.remove(user)

        self.stdout.write(f"dry_run={dry_run}, keep_superuser={keep_superuser}")
        self.stdout.write(f"kept={len(kept)} -> {sorted(kept)}")
        self.stdout.write(f"removed={len(removed)} -> {sorted(removed)}")
