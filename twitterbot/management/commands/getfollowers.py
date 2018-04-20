from django.core.management.base import BaseCommand
from django.conf import settings

import tweepy

from twitterbot.models import TargetTwitterAccount

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


class Command(BaseCommand):

    help = 'Loads followers for given twitter user ' \
           'and saves them to DB (TargetTwitterAccount table)'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)

    def handle(self, *args, **options):

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)

        for user in options['username']:

            self.stdout.write('Loading followers of {}'.format(user))

            try:
                followers_list = api.get_user(user).followers()
                for follower in followers_list:
                    follower_exist = TargetTwitterAccount.objects.filter(
                        user_id=follower.id
                    ).exists()

                    if not follower_exist:
                        follower_info = {
                            'user_id': follower.id,
                            'name': follower.name,
                            'screen_name': follower.screen_name,
                            'followers_count': follower.followers_count
                        }
                        TargetTwitterAccount.objects.create(**follower_info)
                    else:
                        continue

                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded followers of {}'
                                       .format(user)))

            except tweepy.error.TweepError as err:
                raise err
