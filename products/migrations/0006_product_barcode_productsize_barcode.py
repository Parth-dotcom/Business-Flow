
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0005_alter_productsize_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="barcode",
            field=models.CharField(
                max_length=30,
                null=True,
                blank=True,
                default=None,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="productsize",
            name="barcode",
            field=models.CharField(
                max_length=30,
                null=True,
                blank=True,
                default=None,
                db_index=True,
            ),
        ),
    ]
