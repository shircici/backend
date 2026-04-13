from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "List all ops admin users (group-based and settings-based)."

    def handle(self, *args, **options):
        user_model = get_user_model()
        group_users = set()
        settings_users = set(getattr(settings, "OPS_ADMIN_USERNAMES", []))

        group = Group.objects.filter(name="ops_admin").first()
        if group:
            group_users = set(group.user_set.values_list("username", flat=True))

        merged = sorted(group_users | settings_users)
        self.stdout.write("ops_admin users:")
        if not merged:
            self.stdout.write("  (empty)")
            return

        for username in merged:
            user_exists = user_model.objects.filter(username=username).exists()
            source = []
            if username in group_users:
                source.append("group")
            if username in settings_users:
                source.append("settings")
            source_text = ",".join(source) if source else "unknown"
            self.stdout.write(f"  - {username} (source={source_text}, exists={user_exists})")
