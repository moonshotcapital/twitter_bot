import logging
import tweepy
import random

from django.conf import settings
from django.db import IntegrityError

from twitterbot.models import (
    BlackList,
    TargetTwitterAccount,
    TwitterFollower,
    VerifiedUserWithTag
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


def follow_users(limit=200):
    tw_accounts = TargetTwitterAccount.objects.filter(is_follower=False,
                                                      followers_count__gt=800)

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    current_user = api.me()
    if 4801 < current_user.friends_count < 5000:
        limit = 5000 - current_user.followers_count
    elif current_user.friends_count >= 5000:
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

        if tw_user.followers_count > 1000:
            logger.info("Follow %s", user)
            api.create_friendship(tw_user.id)
            user.is_follower = True
            user.save(update_fields=('is_follower', ))
            counter += 1

        if counter == limit:
            logger.info("The limit of %s followings is reached", limit)
            return


def retweet_verified_users():

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    # get random verified user from our DB
    ids_list = VerifiedUserWithTag.objects.all().values_list('id', flat=True)
    user = VerifiedUserWithTag.objects.get(id=random.choice(ids_list))

    # get recent 20 tweets for current user
    recent_tweets = api.user_timeline(user.screen_name)

    counter = 0
    limit = 1  # responsible for how many tweets will be retweeted

    if user and user.tags:
        tag = '#{}'.format(random.choice(user.tags))
    else:
        tag = ''

    for tweet in recent_tweets:
        tw_text = tweet.text.lower()

        if tag in tw_text and not tweet.in_reply_to_status_id and (
                tweet.lang == 'en' or not tweet.in_reply_to_user_id):

            try:
                api.retweet(tweet.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 327 or err.api_code == 185:
                    continue

            counter += 1

        if counter == limit:
            break


def unfollow_users():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    # TODO: add logic for getting list of users for unfollowing process
    # list must contain screen_names or user_ids of Twitter User
    bad_users = TwitterFollower.objects.filter(
        followers_count__lt=1000
    ).values_list('user_id', flat=True)[:300]

    for bad_user in bad_users:
        bad_user = api.get_user(bad_user)
        api.destroy_friendship(bad_user.id)

        # sync our db state due to unfollowing users
        try:
            BlackList.objects.create(user_id=bad_user.id)
            TwitterFollower.objects.filter(user_id=bad_user.id).delete()
        except IntegrityError:
            continue
