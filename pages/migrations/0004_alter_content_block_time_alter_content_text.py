# Generated by Django 5.2 on 2025-05-06 05:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0003_content_block_time_content_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="content",
            name="block_time",
            field=models.BigIntegerField(db_index=True, default=0),
        ),
        migrations.AlterField(
            model_name="content",
            name="text",
            field=models.TextField(default=""),
        ),
    ]
