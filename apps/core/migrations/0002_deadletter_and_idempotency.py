from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiIdempotencyRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("idem_key", models.CharField(max_length=128, unique=True)),
                ("endpoint", models.CharField(db_index=True, max_length=255)),
                ("request_hash", models.CharField(db_index=True, max_length=64)),
                ("response_data", models.JSONField(blank=True, default=dict)),
                ("status_code", models.IntegerField(default=200)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name="DeadLetterTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_name", models.CharField(db_index=True, max_length=128)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField()),
                ("retry_count", models.IntegerField(default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("replayed", "Replayed")], db_index=True, default="pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
