# Generated by Django 2.0.2 on 2019-10-27 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twitterbot', '0010_accountowner_telegram_chat_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='whitelisttwitteruser',
            name='user_id',
            field=models.CharField(max_length=50, null=True),
        ),
    ]