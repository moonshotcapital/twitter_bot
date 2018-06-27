import logging
import tweepy
import random
import requests
import time
from datetime import date

from django.conf import settings
from django.db import IntegrityError
from slackclient import SlackClient

from twitterbot.models import (
    BlackList,
    TargetTwitterAccount,
    TwitterFollower,
    VerifiedUserWithTag,
    WhiteListTwitterUser,
    AccountOwner
)
from utils.common import load_function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET
TWITTER_ACCOUNT_SETTINGS = settings.TWITTER_ACCOUNT_SETTINGS


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


def send_message_to_telegram(message):
    chat_id = settings.TELEGRAM_CHAT_ID
    token = settings.TELEGRAM_NOTIFICATIONS_TOKEN
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    r = requests.post(url, data={'chat_id': chat_id, 'text': message})
    r.raise_for_status()
    logger.info('Sent message to telegram: {}'.format(message))


def make_follow_for_current_account(account_screen_name):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start follow for {}'.format(account.screen_name))
        consumer_key = account.consumer_key
        consumer_secret = account.consumer_secret
        access_token = account.access_token
        access_token_secret = account.access_token_secret

        tw_accounts = TargetTwitterAccount.objects.filter(
            is_follower=False, followers_count__gt=800, account_owner=account)
        today = date.today()

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)

        limit = random.randrange(90, 100)
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
                                                 reason="User not found!",
                                                 account_owner=account)
                        TargetTwitterAccount.objects.filter(
                            user_id=user.user_id, account_owner=account
                        ).delete()
                    except IntegrityError:
                        continue
                    continue
                elif err.api_code == 89:
                    text = 'Twitter access token has been expired. Please,' \
                           ' refresh it in Heroku settings'
                    logger.info(text)
                    send_message_to_slack(text)
                elif err.api_code == 63:
                    continue
                else:
                    raise err

            if tw_user.followers_count > 1000:
                time.sleep(random.randrange(1, 15, step=1))
                logger.info("Follow %s", user)
                try:
                    api.create_friendship(tw_user.id)
                except tweepy.error.TweepError as err:
                    if err.api_code == 161:
                        text = "Unable to follow more people at this time. " \
                               "Account {} must have a sufficient balance of" \
                               " friends and subscribers".format(
                                    account.screen_name
                                )
                        logger.info(text)
                        send_message_to_slack(text)
                        break
                user.is_follower = True
                user.save(update_fields=('is_follower', ))
                counter += 1

            if counter == limit:
                text = "Account: {}. Number of followers: {}." \
                       " Date: {}".format(account.screen_name, limit, today)
                logger.info("The limit of %s followings is reached", limit)
                send_message_to_slack(text)
                send_message_to_telegram(text)
                break
        logger.info('Finish follow for {}'.format(account.screen_name))


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


def make_unfollow_for_current_account(account_screen_name):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start unfollow for {}'.format(account.screen_name))
        consumer_key = account.consumer_key
        consumer_secret = account.consumer_secret
        access_token = account.access_token
        access_token_secret = account.access_token_secret

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)
        me = api.me()
        limit = random.randrange(90, 100)
        logger.info("The limit of unfollowing is set to %s", limit)
        today = date.today()

        followers_list = api.followers_ids()
        friends_list = api.friends_ids()

        count = 0
        for friend in friends_list:
            time.sleep(random.randrange(1, 15, step=1))
            if friend not in followers_list:
                try:
                    api.destroy_friendship(friend)
                except tweepy.error.TweepError as err:
                    if err.api_code == 50:
                        logger.info("User {} not found!".format(friend))
                        continue
                    elif err.api_code == 89:
                        text = 'Twitter access token has been expired. ' \
                               'Please, refresh it!'
                        logger.info(text)
                        send_message_to_slack(text)
                        break
                    elif err.api_code == 63:
                        logger.info("User has been suspended. Error code: 63")
                        continue

                user = api.get_user(friend)
                friendship = api.show_friendship(user.id, user.screen_name,
                                                 me.id, me.screen_name)[0]

                if not friendship.followed_by:
                    logger.info("Unfollow {}".format(friend))
                    count += 1
                    try:
                        BlackList.objects.create(user_id=friend,
                                                 account_owner=account)
                        TwitterFollower.objects.filter(
                            user_id=friend, account_owner=account).delete()
                    except IntegrityError:
                        logger.exception('Integrity Error during unfollowing')
                        continue

            if count == limit:
                break

        text = "Account: {}. Number of unfollowers: {}. Date: {}".format(
            account.screen_name, count, today)
        logger.info(text)
        send_message_to_slack(text)
        send_message_to_telegram(text)
        logger.info('Finish unfollow for {}'.format(account.screen_name))


def follow():
    tw_accounts = AccountOwner.objects.filter(is_active=True)
    for user in tw_accounts:
        allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(user.screen_name)
        if 'follow' in allowed_actions.keys():
            follow_function = allowed_actions.get('follow')
            make_follow = load_function(follow_function)
            make_follow(user.screen_name)


def unfollow():
    tw_accounts = AccountOwner.objects.filter(is_active=True)
    for user in tw_accounts:
        allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(user.screen_name)
        if 'unfollow' in allowed_actions.keys():
            unfollow_function = allowed_actions.get('unfollow')
            make_unfollow = load_function(unfollow_function)
            make_unfollow(user.screen_name)
