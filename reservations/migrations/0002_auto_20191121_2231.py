# Generated by Django 2.2.7 on 2019-11-21 13:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reservation',
            old_name='chech_out',
            new_name='check_out',
        ),
    ]
