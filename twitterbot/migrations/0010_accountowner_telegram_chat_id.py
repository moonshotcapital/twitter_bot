# Generated by Django 2.0.2 on 2019-09-29 18:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twitterbot', '0009_auto_20180625_1515'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountowner',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]