import logging
import tweepy

from django.conf import settings
from django.db import IntegrityError

from twitterbot.models import TargetTwitterAccount, BlackList

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
    elif current_user.followers_count >= 5000:
        # TODO: delete this elif block when 'goformoonshot' account will have
        # a sufficient balance of friends and subscribers
        return

    counter = 0
    for user in tw_accounts:

        try:
            tw_user = api.get_user(user.user_id)
        except tweepy.error.TweepError as err:
            if err.api_code == 50:
                print("User {} not found!".format(user.name))
                try:
                    BlackList.objects.create(user_id=user.user_id,
                                             reason="User not found!")
                    TargetTwitterAccount.objects.filter(user_id=user.user_id).delete()
                except IntegrityError:
                    continue
                continue
            else:
                raise err

        if tw_user.followers_count > 300:
            logger.info("Follow %s", user)
            api.create_friendship(tw_user.id)
            user.is_follower = True
            user.save(update_fields=('is_follower', ))
            counter += 1

        if counter == limit:
            logger.info("The limit of %s followings is reached", limit)
            return
