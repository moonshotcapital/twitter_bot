import logging
import tweepy
import random

from django.conf import settings
from django.db import IntegrityError
from slackclient import SlackClient

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


def send_message_to_slack(message):
    sc = SlackClient(settings.SLACK_API_TOKEN)
    channel = settings.SLACK_CHANNEL
    sc.api_call(
        "chat.postMessage",
        channel=channel,
        text=message,
        username='@twitter-notifier'
    )
    logger.info('Sent message to slack: {}'.format(message))


def follow_users():
    tw_accounts = TargetTwitterAccount.objects.filter(is_follower=False,
                                                      followers_count__gt=800)

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    limit = random.randrange(350, 650)
    logger.info("The limit of followers is set to %s", limit)
    counter = 0
    for user in tw_accounts:

        try:
            tw_user = api.get_user(user.user_id)
        except tweepy.error.TweepError as err:
            if err.api_code == 50:
                logger.info("User {} not found!".format(user.name))
                try:
                    BlackList.objects.create(user_id=user.user_id,
                                             reason="User not found!")
                    TargetTwitterAccount.objects.filter(user_id=user.user_id).delete()
                except IntegrityError:
                    continue
                continue
            elif err.api_code == 89:
                text = 'Twitter access token is expired. Please,' \
                       ' refresh it in heroku settings'
                logger.info(text)
                send_message_to_slack(text)
            else:
                raise err

        if tw_user.followers_count > 1000:
            logger.info("Follow %s", user)
            try:
                api.create_friendship(tw_user.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 161:
                    text = "Unable to follow more people at this time. " \
                           "Account must have a sufficient balance of " \
                           "friends and subscribers"
                    logger.info(text)
                    send_message_to_slack(text)
                    return
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

    if user and user.tags:
        tag = '#{}'.format(random.choice(user.tags))
    else:
        tag = ''

    result = make_retweet(api, recent_tweets, tag=tag)
    if not result:
        make_retweet(api, recent_tweets)


def make_retweet(api, recent_tweets, tag=''):
    for tweet in recent_tweets:
        tw_text = tweet.text.lower()

        if tag in tw_text and not tweet.in_reply_to_status_id and (
                tweet.lang == 'en' and not tweet.in_reply_to_user_id):

            try:
                api.retweet(tweet.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 327 or err.api_code == 185:
                    continue
            return True
    return False


def unfollow_users():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    limit = random.randrange(350, 650)
    logger.info("The limit of unfollowing is set to %s", limit)

    # TODO: add logic for getting list of users for unfollowing process
    # list must contain screen_names or user_ids of Twitter User
    bad_users = TwitterFollower.objects.values_list('user_id',
                                                    flat=True)[:limit]

    for bad_user in bad_users:
        try:
            bad_user = api.get_user(bad_user)
            result = api.destroy_friendship(bad_user.id)
        except tweepy.error.TweepError as err:
            if err.api_code == 50:
                logger.info("User {} not found!".format(bad_user.name))
                continue
            elif err.api_code == 89:
                text = 'Twitter access token is expired. Please,' \
                       ' refresh it in Heroku settings'
                logger.info(text)
                send_message_to_slack(text)
                return

        # sync our db state due to unfollowing users
        if not result.following:
            try:
                BlackList.objects.create(user_id=bad_user.id)
                TwitterFollower.objects.filter(user_id=bad_user.id).delete()
            except IntegrityError:
                continue
