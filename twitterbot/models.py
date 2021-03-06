from django.db import models
from django.contrib.postgres.fields import ArrayField


class AccountOwner(models.Model):
    screen_name = models.CharField(max_length=50, unique=True)
    consumer_key = models.CharField(max_length=50, null=True, blank=True)
    consumer_secret = models.CharField(max_length=50, null=True, blank=True)
    access_token = models.CharField(max_length=50, null=True, blank=True)
    access_token_secret = models.CharField(max_length=50, null=True,
                                           blank=True)
    is_active = models.BooleanField(default=False)
    telegram_chat_id = models.CharField(max_length=10, null=True, blank=True)
    followers_limit = models.PositiveIntegerField(default=25)

    # send daily csv statistic about followers increasing
    csv_statistic = models.BooleanField(default=False)

    # follow accounts that follow this account (without using bot)
    follow_all_followers = models.BooleanField(default=False)

    # follow only target accounts that have 400+ followers
    target_account_followers_count = models.PositiveIntegerField(default=400)

    # path of the retweet function
    retweet_func = models.CharField(max_length=100, null=True, blank=True)

    keywords = ArrayField(
        models.CharField(max_length=100), null=True, blank=True,
        help_text='words searched in description of target accounts'
    )

    def __str__(self):
        return self.screen_name


class TwitterFollower(models.Model):

    FRIEND = 1
    FOLLOWER = 2

    USER_TYPE_CHOICES = ((FRIEND, 'Friend'), (FOLLOWER, 'Follower'))

    user_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    screen_name = models.CharField(max_length=50)
    followers_count = models.PositiveIntegerField(null=True)
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, null=True)

    location = models.CharField(max_length=200, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    account_owner = models.ForeignKey(AccountOwner, on_delete=models.CASCADE,
                                      null=True)
    is_favourite = models.BooleanField(default=False)

    class Meta:
        db_table = 'twitter_followers'
        unique_together = ('screen_name', 'account_owner', 'user_type')

    def __str__(self):
        return self.screen_name


class TargetTwitterAccount(models.Model):
    user_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    screen_name = models.CharField(max_length=50)
    followers_count = models.PositiveIntegerField(null=True)
    is_follower = models.BooleanField(default=False)

    location = models.CharField(max_length=200, blank=True, null=True)
    account_owner = models.ForeignKey(AccountOwner, on_delete=models.CASCADE,
                                      null=True)

    class Meta:
        db_table = 'target_twitter_accounts'
        unique_together = ('user_id', 'account_owner')

    def __str__(self):
        return self.screen_name


class BlackList(models.Model):
    user_id = models.CharField(max_length=50, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    reason = models.CharField(max_length=500, null=True, blank=True)
    account_owner = models.ForeignKey(AccountOwner, on_delete=models.CASCADE,
                                      null=True)

    class Meta:
        db_table = 'twitter_blacklist'
        unique_together = ('user_id', 'account_owner')

    def __str__(self):
        return '{} - {}'.format(self.user_id, self.reason)


class VerifiedUserWithTag(models.Model):
    """
    This model contains users whom we are going to retweet using tags
    """

    screen_name = models.CharField(max_length=50)
    tags = ArrayField(models.CharField(max_length=50), null=True, blank=True)
    account_owner = models.ForeignKey(AccountOwner, on_delete=models.CASCADE,
                                      null=True)

    class Meta:
        db_table = 'twitter_users_with_tags'
        unique_together = ('screen_name', 'account_owner')

    def __str__(self):
        return self.screen_name


class WhiteListTwitterUser(models.Model):
    user_id = models.CharField(max_length=50, null=True)
    screen_name = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    account_owner = models.ForeignKey(AccountOwner, on_delete=models.CASCADE,
                                      null=True)

    class Meta:
        db_table = 'white_list'

    def __str__(self):
        return self.screen_name


class RunTasksTimetable(models.Model):
    name = models.CharField(max_length=100)
    execution_time = models.DateTimeField()
    executed = models.BooleanField(default=False)
    failed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'run_tasks'

    def __str__(self):
        return self.name
