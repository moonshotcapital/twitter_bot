import logging
from django.core.management.base import BaseCommand
from django.conf import settings

import tweepy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


class Command(BaseCommand):

    help = 'Likes tweets that contain specific tags'

    def add_arguments(self, parser):
        parser.add_argument('tags', nargs='+', type=str)

    def handle(self, *args, **options):

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)

        query = ' '.join(['#{}'.format(i) for i in options['tags']])
        counter = 0
        for tweet in tweepy.Cursor(api.search, q=query, lang='en').items(40):
            if tweet.retweet_count > 10 or tweet.favorite_count > 20:
                try:
                    api.create_favorite(tweet.id)
                except tweepy.error.TweepError as err:
                    if err.api_code == 139:
                        continue
                    else:
                        raise err
                counter += 1
                self.stdout.write(
                    self.style.SUCCESS('Successfully liked tweet id {}'
                                       ' with text: {}'
                                       .format(tweet.id, tweet.text)))
            if counter == 2:
                return
