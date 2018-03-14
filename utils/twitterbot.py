import logging
import time
import tweepy

from django.conf import settings
from twitterbot.models import TargetTwitterAccounts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main(limit=1000):
    list_users = TargetTwitterAccounts.objects.values_list('twitter_url', flat=True)

    consumer_key = settings.CONSUMER_KEY
    consumer_secret = settings.CONSUMER_SECRET
    access_token = settings.ACCESS_TOKEN
    access_token_secret = settings.ACCESS_TOKEN_SECRET

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(
        auth, wait_on_rate_limit=True,
        wait_on_rate_limit_notify=True,
        retry_count=10, retry_delay=5,
        retry_errors=None
    )

    current_user = api.me().screen_name
    cached_users = cache_handler(api, current_user)
    counter = 0

    for user in list_users:
        if user and user not in cached_users:
            user = user.split('/')[3]
            try:
                if api.get_user(user).followers_count > 300:
                    logger.info("Follow %s", user)
                    api.create_friendship(user)
            except tweepy.error.TweepError:
                logger.exception('')
            cached_users.append(user)
            counter += 1
            if counter >= limit:
                logger.info("The limit of %s followings is reached", limit)
                return
        else:
            logger.info("Skipped %s", user)


def cache_handler(api, current_user):
    usernames = []
    logger.info(
        "Start fetching %s follwers into local cache", current_user)
    for page in tweepy.Cursor(api.friends_ids,
                              screen_name=current_user).pages():
        wanted_parts = round(len(page) / 100) + 1
        parts = split_list(page, wanted_parts)
        for part in parts:
            users_part = api.lookup_users(user_ids=part)
            for username in users_part:
                usernames.append(username.screen_name)
        logger.debug("Part finished. Waiting 60 seconds to continue")
        time.sleep(60)
    logger.info("Finished fetching followers to local cache")
    return usernames


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]
