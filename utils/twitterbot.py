import logging
import tweepy

from django.conf import settings
from twitterbot.models import TargetTwitterAccount

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


def follow_users(limit=200):
    tw_accounts = TargetTwitterAccount.objects.filter(is_follower=False)

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    current_user = api.me()
    if 4801 < current_user.followers_count < 5000:
        limit = 5000 - current_user.followers_count

    counter = 0
    for user in tw_accounts:

        if api.get_user(user.user_id).followers_count > 300:
            logger.info("Follow %s", user)
            api.create_friendship(user.user_id)
            user.is_follower = True
            user.save(update_fields=('is_follower', ))
            counter += 1

        if counter == limit:
            logger.info("The limit of %s followings is reached", limit)
            return
