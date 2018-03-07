from django.db import models


class TwitterUser(models.Model):
    user_id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    screen_name = models.CharField(max_length=50)
    location = models.CharField(max_length=200, null=True)
    url = models.URLField(null=True)
    description = models.CharField(max_length=200, null=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'twitter_users'

    def __str__(self):
        return self.name


class Followers(models.Model):
    user_id1 = models.ForeignKey(TwitterUser, on_delete=models.CASCADE, related_name='publisher')
    user_id2 = models.ForeignKey(TwitterUser, on_delete=models.CASCADE, related_name='subscriber')

    class Meta:
        db_table = 'followers'

    def __str__(self):
        return '{} follows {}'.format(self.user_id2.name, self.user_id1.name)


class TargetTwitterAccounts(models.Model):
    first_name = models.CharField(max_length=100, db_index=True)
    last_name = models.CharField(max_length=100, db_index=True)
    twitter_url = models.URLField(null=True)
    title = models.CharField(max_length=200, blank=True, null=True,
                             db_index=True)
    location_city = models.CharField(max_length=100, blank=True, null=True)
    location_region = models.CharField(max_length=100, blank=True, null=True)
    location_country_code = models.CharField(max_length=100, blank=True,
                                             null=True)
    organization = models.CharField(max_length=100, blank=True, null=True,
                                    db_index=True)

    class Meta:
        db_table = 'target_twitter_accounts'

    @property
    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    @property
    def location(self):
        return '{} {} {}'.format(self.location_city, self.location_region,
                                 self.location_country_code)


class BlackList(models.Model):
    twitter_username = models.CharField(max_length=100, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    reason = models.CharField(max_length=255)
    description = models.CharField(max_length=1000)

    class Meta:
        db_table = 'twitter_blacklist'

    def __str__(self):
        return f"{self.twitter_username} - {self.reason}"
