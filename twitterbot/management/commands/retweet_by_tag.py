import logging

import tweepy
from django.conf import settings
from django.core.management.base import BaseCommand

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


class Command(BaseCommand):

    help = ('Retweet 2 tweets by hashtags. Search will use all entered tweets'
            ' together, NOT in separate mode')

    def add_arguments(self, parser):
        parser.add_argument('tags', nargs='+', type=str)

    def handle(self, *args, **options):
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)

        query = ' '.join(['#{}'.format(i) for i in options['tags']])
        counter = 0
        for tweet in tweepy.Cursor(api.search, q=query, lang='en').items(180):
            try:
                api.retweet(tweet.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 327 or err.api_code == 185:
                    continue
                else:
                    raise err
            counter += 1
            self.stdout.write(
                self.style.SUCCESS('Successfully retweeted tweet id {}'
                                   ' with text: {}'
                                   .format(tweet.id, tweet.text)))
            if counter == 1:
                return
