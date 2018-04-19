from django.db import models


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

    class Meta:
        db_table = 'twitter_followers'

    def __str__(self):
        return self.screen_name


class TargetTwitterAccount(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    screen_name = models.CharField(max_length=50)
    followers_count = models.PositiveIntegerField(null=True)

    location_city = models.CharField(max_length=100, blank=True, null=True)
    location_region = models.CharField(max_length=100, blank=True, null=True)
    location_country_code = models.CharField(max_length=100, blank=True,
                                             null=True)
    organization = models.CharField(max_length=100, blank=True, null=True,
                                    db_index=True)

    class Meta:
        db_table = 'target_twitter_accounts'

    @property
    def location(self):
        return '{} {} {}'.format(self.location_city, self.location_region,
                                 self.location_country_code)


class BlackList(models.Model):
    user_id = models.CharField(max_length=50, unique=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    reason = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'twitter_blacklist'

    def __str__(self):
        return '{} - {}'.format(self.user_id, self.reason)
