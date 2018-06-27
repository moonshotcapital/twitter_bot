# Generated by Django 2.0.2 on 2018-06-25 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twitterbot', '0008_auto_20180625_0757'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blacklist',
            name='user_id',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='targettwitteraccount',
            name='user_id',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='verifieduserwithtag',
            name='screen_name',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterUniqueTogether(
            name='blacklist',
            unique_together={('user_id', 'account_owner')},
        ),
        migrations.AlterUniqueTogether(
            name='targettwitteraccount',
            unique_together={('user_id', 'account_owner')},
        ),
        migrations.AlterUniqueTogether(
            name='twitterfollower',
            unique_together={('screen_name', 'account_owner', 'user_type')},
        ),
        migrations.AlterUniqueTogether(
            name='verifieduserwithtag',
            unique_together={('screen_name', 'account_owner')},
        ),
    ]