# Generated by Django 3.2 on 2024-04-14 22:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0002_dentist_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='dentist',
            name='sub_title',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
    ]
