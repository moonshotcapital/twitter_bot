import logging
import tweepy
import random
import requests
import time
from datetime import date, datetime, timedelta

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


def send_message_to_telegram(message, account):
    token = settings.TELEGRAM_NOTIFICATIONS_TOKEN
    url = "https://api.telegram.org/bot{}/sendMessage".format(token)
    r = requests.post(url, data={'chat_id': account.telegram_chat_id,
                                 'text': message})
    r.raise_for_status()
    logger.info('Sent message to telegram: {}'.format(message))


def get_count_of_followers_and_following(api):
    data = api.me()
    return data.followers_count, data.friends_count


def make_follow_for_current_account(account_screen_name, limit):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start follow for {}'.format(account.screen_name))
        api = connect_to_twitter_api(account)
        before_stat = get_count_of_followers_and_following(api)
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
                    send_message_to_telegram(text, account)
                    break
                elif err.api_code == 63:
                    logger.info("User has been suspended. Error code: 63")
                    continue
                else:
                    raise err

            if tw_user and tw_user.followers_count > 400:
                time.sleep(random.randrange(10, 60))
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
                        send_message_to_telegram(text, account)
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

        stats = get_count_of_followers_and_following(api)
        text = ("Finished following. Account: {}. Number of followers: {}."
                " We're following {}. Following before task: {}. Date: {}."
                .format(account.screen_name, *stats, before_stat[1], today))
        send_message_to_slack(text)
        send_message_to_telegram(text, account)
        logger.info('Finish follow for {}'.format(account.screen_name))


def retweet():
    for user in TWITTER_ACCOUNT_SETTINGS.keys():
        allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(user)
        is_active = AccountOwner.objects.filter(is_active=True,
                                                screen_name=user).exists()
        if is_active and 'retweet' in allowed_actions.keys():
            make_retweet = load_function(allowed_actions.get('retweet')[0])
            logger.info('Start retweeting for {}'.format(user))
            user = AccountOwner.objects.get(is_active=True, screen_name=user)
            make_retweet(user)
            logger.info('Finish retweeting for {}'.format(user))


def retweet_verified_users_with_tag(user):
    today = date.today()
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
            msg = 'New retweet for {}. Date: {}'.format(user, today)
            send_message_to_slack(msg)
            return


def retweet_verified_users(user):
    today = datetime.today()
    last_tweet = today - timedelta(days=1)
    last_five_days = today - timedelta(days=5)

    api = connect_to_twitter_api(user)
    ver_users = VerifiedUserWithTag.objects.filter(
        account_owner=user
    )
    tweets_to_retweet = []
    for ver_user in ver_users:
        time.sleep(random.randrange(10, 60))
        recent_tweets = api.user_timeline(ver_user.screen_name,
                                          exclude_replies=True,
                                          count=100)
        for tweet in recent_tweets:
            if tweet.created_at < last_tweet:
                break
            if 5 < tweet.retweet_count < 30 and tweet.lang == 'en':
                try:
                    tweet.retweeted_status
                except AttributeError:
                    tweets_to_retweet.append(tweet)

    max_retweets = sorted(tweets_to_retweet,
                          key=lambda tw: tw.retweet_count,
                          reverse=True)

    twitter_posts = api.me().timeline()
    last_five_days_tweets = [
        x.retweeted_status.user.screen_name for x in twitter_posts
        if x.created_at > last_five_days and x.retweeted is True
    ]

    for tweet in max_retweets:
        if tweet.user.screen_name not in last_five_days_tweets:
            try:
                api.retweet(tweet.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 327 or err.api_code == 185:
                    logger.info('Error code {}'.format(err.api_code))
                    continue
            msg = '{} retweeted {} tweet!. Date: {}'.format(
                user, tweet.user.screen_name, today)
            send_message_to_slack(msg)
            send_message_to_telegram(msg, user)
            return


def make_unfollow_for_current_account(account_screen_name, limit):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start unfollow for {}'.format(account.screen_name))
        api = connect_to_twitter_api(account)
        me = api.me()
        following = me.friends_count
        limit = random.randrange(max(limit-10, 1), limit)
        logger.info("The limit of unfollowing is set to %s", limit)
        today = date.today()

        followers_list = api.followers_ids()
        friends_list = api.friends_ids()
        not_in_followers = [x for x in friends_list if x not in followers_list]

        count = 0
        for friend in not_in_followers:
            time.sleep(random.randrange(10, 60))

            user = TwitterFollower.objects.filter(user_id=friend).exists()
            if user:
                user = TwitterFollower.objects.filter(user_id=friend).first()
                user_for_unfollow = user.screen_name
            else:
                user_for_unfollow = api.get_user(friend).screen_name

            in_white_list = WhiteListTwitterUser.objects.filter(
                screen_name=user_for_unfollow).exists()
            if in_white_list:
                continue

            try:
                api.destroy_friendship(friend)
                time.sleep(random.randrange(10, 60))
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
                    send_message_to_telegram(text, account)
                    break
                elif err.api_code == 63:
                    logger.info("User has been suspended. Error code: 63")
                    continue

            if friendship and not friendship.followed_by:
                logger.info("Unfollow {}".format(friend))
                try:
                    BlackList.objects.create(user_id=friend,
                                             account_owner=account)
                    TwitterFollower.objects.filter(
                        user_id=friend, account_owner=account).delete()
                except IntegrityError:
                    logger.exception('Integrity Error during unfollowing')
                    continue

            count += 1
            if count == limit:
                break
        stats = get_count_of_followers_and_following(api)
        text = ("Finished unfollowing. Account: {}. Number of followers: {}."
                " We're following {}. Following before task: {}. Date: {}."
                .format(account.screen_name, *stats, following, today))
        logger.info(text)
        send_message_to_slack(text)
        send_message_to_telegram(text, account)
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


def follow_all_own_followers(account_screen_name, limit=0):
    account = AccountOwner.objects.get(is_active=True,
                                       screen_name=account_screen_name)
    if account:
        logger.info('Start follow own followers for {}'.format(
            account.screen_name)
        )
        api = connect_to_twitter_api(account)
        me = api.me()
        limit = random.randrange(limit, limit+10)
        logger.info("The limit of followers is set to %s", limit)
        today = date.today()

        followers_list = api.followers_ids()
        friends_list = api.friends_ids()
        not_in_friends = [x for x in followers_list if x not in friends_list]

        count = 0
        for follower in not_in_friends:
            time.sleep(random.randrange(10, 60))
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
                    send_message_to_telegram(text, account)
                    break
                elif err.api_code == 63:
                    logger.info("User has been suspended. Error code: 63")
                    continue
            logger.info("Follow %s", follower)
            count += 1
            if count == limit:
                logger.info("The limit of %s followings is reached", limit)
                break
        text = "Account: {}. Follow {} own followers." \
               " Date: {}".format(account.screen_name, count, today)
        send_message_to_slack(text)
        send_message_to_telegram(text, account)

        if count == 0:
            text = 'TwitterBot finished follow own {}\'s followers. You can' \
                   ' delete related function from' \
                   ' TWITTER_ACCOUNT_SETTINGS'.format(account_screen_name)
            send_message_to_slack(text)
