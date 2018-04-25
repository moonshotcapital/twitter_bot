import logging
from django.conf import settings

import tweepy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


HASHTAG_QUERY = [
    '#ios',
    '#iosdev',
    '#itunesconnect',
    '#appstore',
    '#googleplay',
    '#mobileapps',
    '#mobilegames',
    '#appdev',
    '#appdevelopement',
    '#appbusiness',
    '#gamedev',
    '#ASO',
    '#appstoreoptimization',
    '#mobile growth',
    '#appmarketing',
    '#mobilemarketing',
    '#digitalmarketing',
    '#appanalytics',
    '#mobileanalytics',
    '#mobile',
    '#useracquisition',
    '#ROI',
    '#entrepreneur',
    '#growthhacking',
    '#indiedev'
]


def retweet_by_tag():

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    # TODO: need to define how many and which tweets need to be retweeted
    max_tweets = 10
    query = HASHTAG_QUERY[0]
    searched_tweets = [tweet for tweet in tweepy.Cursor(
        api.search, q=query, lang='en').items(max_tweets)]

    for tweet in searched_tweets:
        if tweet.user.followers_count > 300 \
                and tweet.retweet_count > 50 and tweet.favorite_count > 50:
            api.retweet(tweet.id)
            logger.info('Retweet %s', tweet.id)
