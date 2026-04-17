from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create Django Groups used for RBAC (idempotent)."

    def handle(self, *args, **options):
        names = [
            "api_integrator",
            "ops_admin",
            "selection_decision_maker",
            "management",
            "order_editor",
        ]
        for name in names:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"created group: {name}"))
            else:
                self.stdout.write(f"group exists: {name}")
            if name == "order_editor":
                perm = Permission.objects.filter(codename="order_edit", content_type__app_label="core").first()
                if perm:
                    group.permissions.add(perm)
                    self.stdout.write(self.style.SUCCESS("bound permission core.order_edit -> order_editor"))
        self.stdout.write(self.style.SUCCESS("create_rbac_groups done"))
