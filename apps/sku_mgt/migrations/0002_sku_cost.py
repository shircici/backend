from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sku_mgt", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sku",
            name="cost",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="采购/供货成本；为空时选品引擎可回退为售价比例估算",
                max_digits=10,
                null=True,
            ),
        ),
    ]
