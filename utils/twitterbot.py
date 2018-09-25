import logging
import tweepy
import random
import requests
import time
from datetime import date

from django.conf import settings
from django.db import IntegrityError
from requests.exceptions import HTTPError
from slackclient import SlackClient

from twitterbot.models import (
    BlackList,
    TargetTwitterAccount,
    TwitterFollower,
    VerifiedUserWithTag,
    WhiteListTwitterUser,
    AccountOwner
)
from utils.common import load_function, connect_to_twitter_api

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


def login_to_twitter_api(account: AccountOwner):
    consumer_key = account.consumer_key
    consumer_secret = account.consumer_secret
    access_token = account.access_token
    access_token_secret = account.access_token_secret
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)
    return api


def make_follow_for_current_account(account_screen_name, limit):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start follow for {}'.format(account.screen_name))
        api = login_to_twitter_api(account)
        tw_accounts = TargetTwitterAccount.objects.filter(
            is_follower=False, followers_count__gt=400, account_owner=account)
        today = date.today()

        limit = random.randrange(limit, limit+10)
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
                           ' refresh it for {}'.format(account.screen_name)
                    logger.info(text)
                    send_message_to_slack(text)
                    send_message_to_telegram(text)
                    break
                elif err.api_code == 63:
                    logger.info("User has been suspended. Error code: 63")
                    continue
                else:
                    raise err

            if tw_user and tw_user.followers_count > 400:
                time.sleep(random.randrange(1, 3, step=1))
                try:
                    api.create_friendship(tw_user.id)
                    tweets = tw_user.timeline()[:2]  # get 2 tweets for like
                    for tweet in tweets:
                        api.create_favorite(tweet.id)

                except tweepy.error.TweepError as err:
                    if err.api_code == 161:
                        text = "Unable to follow more people at this time. " \
                               "Account {} must have a sufficient balance of" \
                               " friends and subscribers".format(
                                    account.screen_name
                                )
                        logger.info(text)
                        send_message_to_slack(text)
                        send_message_to_telegram(text)
                        break
                    elif err.api_code == 139:
                        logger.info('Like tweet which have already favorited!')
                logger.info("Follow %s", user)
                user.is_follower = True
                user.save(update_fields=('is_follower', ))
                counter += 1

            if counter == limit:
                logger.info("The limit of %s followings is reached", limit)
                break

        text = "Account: {}. Number of followers: {}." \
               " Date: {}".format(account.screen_name, limit, today)
        send_message_to_slack(text)
        send_message_to_telegram(text)
        logger.info('Finish follow for {}'.format(account.screen_name))


def retweet_verified_users():
    today = date.today()
    for user in TWITTER_ACCOUNT_SETTINGS.keys():
        allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(user)
        is_active = AccountOwner.objects.filter(is_active=True,
                                                screen_name=user).exists()
        if is_active and allowed_actions.get('retweet'):
            logger.info('Start retweeting for {}'.format(user))
            user = AccountOwner.objects.get(is_active=True, screen_name=user)
            api = connect_to_twitter_api(user)

            # get random verified user from our DB
            ids_list = VerifiedUserWithTag.objects.filter(
                account_owner=user
            ).values_list('id', flat=True)
            ver_user = VerifiedUserWithTag.objects.get(
                id=random.choice(ids_list), account_owner=user)

            # get recent 20 tweets for current user
            recent_tweets = api.user_timeline(ver_user.screen_name)

            if ver_user and ver_user.tags:
                tag = '#{}'.format(random.choice(ver_user.tags))
            else:
                tag = ''

            result = make_retweet(api, recent_tweets, tag=tag)
            if not result:
                make_retweet(api, recent_tweets)
            msg = 'New retweet for {}. Date: {}'.format(user, today)
            send_message_to_slack(msg)
            logger.info('Finish retweeting for {}'.format(user))


def make_retweet(api, recent_tweets, tag=''):
    for tweet in recent_tweets:
        tw_text = tweet.text.lower()

        if tag in tw_text and not tweet.in_reply_to_status_id and (
                tweet.lang == 'en' and not tweet.in_reply_to_user_id):

            try:
                api.retweet(tweet.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 327 or err.api_code == 185:
                    logger.info('Error code {}'.format(err.api_code))
                    continue
            return True
    return False


def make_unfollow_for_current_account(account_screen_name, limit):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start unfollow for {}'.format(account.screen_name))
        api = login_to_twitter_api(account)
        me = api.me()
        limit = random.randrange(limit-10, limit)
        logger.info("The limit of unfollowing is set to %s", limit)
        today = date.today()

        followers_list = api.followers_ids()
        friends_list = api.friends_ids()

        count = 0
        for friend in friends_list:
            time.sleep(random.randrange(1, 3, step=1))

            user = TwitterFollower.objects.filter(user_id=friend).exists()
            if user:
                user = TwitterFollower.objects.filter(user_id=friend).first()
                user_for_unfollow = user.screen_name
            else:
                user_for_unfollow = api.get_user(friend)

            in_white_list = WhiteListTwitterUser.objects.filter(
                screen_name=user_for_unfollow).exists()
            if in_white_list:
                continue

            if friend not in followers_list:
                try:
                    api.destroy_friendship(friend)
                    time.sleep(random.randrange(1, 3, step=1))
                    user = api.get_user(friend)
                    friendship = api.show_friendship(user.id, user.screen_name,
                                                     me.id, me.screen_name)[0]
                except tweepy.error.TweepError as err:
                    if err.api_code == 50:
                        logger.info("User {} not found!".format(friend))
                        continue
                    elif err.api_code == 89:
                        text = 'Twitter access token has been expired.' \
                               'Please, refresh it for {}'.format(
                                me.screen_name
                                )
                        logger.info(text)
                        send_message_to_slack(text)
                        send_message_to_telegram(text)
                        break
                    elif err.api_code == 63:
                        logger.info("User has been suspended. Error code: 63")
                        continue

                if friendship and not friendship.followed_by:
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
    for user in TWITTER_ACCOUNT_SETTINGS.keys():
        allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(user)
        is_active = AccountOwner.objects.filter(is_active=True,
                                                screen_name=user).exists()
        if is_active and 'follow' in allowed_actions.keys():
            for follow_func in allowed_actions.get('follow'):
                make_follow = load_function(follow_func)
                limit = allowed_actions.get('followers_limit')
                try:
                    make_follow(user, limit)
                except (tweepy.error.TweepError, HTTPError):
                    logger.exception('Something gone wrong')
                    continue


def unfollow():
    for user in TWITTER_ACCOUNT_SETTINGS.keys():
        allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(user)
        is_active = AccountOwner.objects.filter(is_active=True,
                                                screen_name=user).exists()
        if is_active and 'unfollow' in allowed_actions.keys():
            for unfollow_func in allowed_actions.get('unfollow'):
                make_unfollow = load_function(unfollow_func)
                limit = allowed_actions.get('followers_limit')
                try:
                    make_unfollow(user, limit)
                except (tweepy.error.TweepError, HTTPError):
                    logger.exception('Something gone wrong')
                    continue


def follow_all_own_followers(account_screen_name, limit=None):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start follow own followers for {}'.format(
            account.screen_name)
        )
        api = login_to_twitter_api(account)
        me = api.me()
        limit = random.randrange(limit, limit+10)
        logger.info("The limit of followers is set to %s", limit)
        today = date.today()

        followers_list = api.followers_ids()
        friends_list = api.friends_ids()

        count = 0
        for follower in followers_list:
            time.sleep(random.randrange(1, 15, step=1))

            if follower not in friends_list:
                try:
                    api.create_friendship(follower)
                except tweepy.error.TweepError as err:
                    if err.api_code == 50:
                        logger.info("User {} not found!".format(follower.id))
                        continue
                    elif err.api_code == 89:
                        text = 'Twitter access token has been expired.' \
                               'Please, refresh it for {}'.format(
                                me.screen_name
                                )
                        logger.info(text)
                        send_message_to_slack(text)
                        send_message_to_telegram(text)
                        break
                    elif err.api_code == 63:
                        logger.info("User has been suspended. Error code: 63")
                        continue
                logger.info("Follow %s", follower)
                count += 1
            if count == limit:
                text = "Account: {}. Follow {} own followers." \
                       " Date: {}".format(account.screen_name, limit, today)
                logger.info("The limit of %s followings is reached", limit)
                send_message_to_slack(text)
                send_message_to_telegram(text)
                break

        if count == 0:
            text = 'TwitterBot finished follow own {}\'s followers. You can' \
                   ' delete related function from' \
                   ' TWITTER_ACCOUNT_SETTINGS'.format(account_screen_name)
            send_message_to_slack(text)
