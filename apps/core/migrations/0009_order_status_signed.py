from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0008_logistics_rate_card"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("paid", "Paid"),
                    ("shipped", "Shipped"),
                    ("signed", "Signed"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
    ]
