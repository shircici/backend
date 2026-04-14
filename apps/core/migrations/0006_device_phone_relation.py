from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_auth_and_sms_hub"),
    ]

    operations = [
        migrations.CreateModel(
            name="DevicePhoneRelation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_id", models.CharField(db_index=True, max_length=128)),
                ("phone", models.CharField(db_index=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
        ),
    ]
