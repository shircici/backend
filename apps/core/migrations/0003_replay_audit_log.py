from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_deadletter_and_idempotency"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReplayAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operator", models.CharField(db_index=True, default="system", max_length=128)),
                ("result", models.CharField(db_index=True, default="success", max_length=32)),
                ("detail", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("dead_letter_task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replay_logs", to="core.deadlettertask")),
            ],
        ),
    ]
