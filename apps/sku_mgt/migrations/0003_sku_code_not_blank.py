from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sku_mgt', '0002_sku_cost'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sku',
            name='sku_code',
            field=models.CharField(db_index=True, max_length=64),
        ),
    ]
