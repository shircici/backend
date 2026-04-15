from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create Django Groups used for RBAC (idempotent)."

    def handle(self, *args, **options):
        names = [
            "api_integrator",
            "ops_admin",
            "selection_decision_maker",
            "management",
        ]
        for name in names:
            _, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"created group: {name}"))
            else:
                self.stdout.write(f"group exists: {name}")
        self.stdout.write(self.style.SUCCESS("create_rbac_groups done"))
