import logging
import re
import tweepy
import random
import time
from datetime import date, datetime, timedelta

from django.db import IntegrityError
from requests.exceptions import HTTPError

from twitterbot.models import (
    BlackList,
    TargetTwitterAccount,
    TwitterFollower,
    VerifiedUserWithTag,
    WhiteListTwitterUser,
    AccountOwner
)
from utils.common import (
    load_function, connect_to_twitter_api,
    send_message_to_slack, send_message_to_telegram
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T_MIN = 60
T_MAX = 120
LIKES = 10


def get_count_of_followers_and_following(api):
    data = api.me()
    return data.followers_count, data.friends_count


def make_follow_for_current_account(account):
    """Follow twitter accounts for current account owner"""
    logger.info('Start follow for {}'.format(account.screen_name))
    api = connect_to_twitter_api(account)
    before_stat = get_count_of_followers_and_following(api)
    _follow_target_accounts(account, api)
    stats = get_count_of_followers_and_following(api)
    text = ("Finished following. Account: {}. Number of followers: {}."
            " We're following {}. Following before task: {}. Date: {}."
            .format(account.screen_name, *stats, before_stat[1], date.today()))
    send_message_to_slack(text)
    send_message_to_telegram(text, account)
    logger.info(text)


def _follow_target_accounts(account, api):
    """Follow target twitter accounts of current twitter account owner"""
    limit = random.randrange(account.followers_limit - 10,
                             account.followers_limit)
    logger.info("The limit of followers is set to %s", limit)
    target_accounts = TargetTwitterAccount.objects.filter(
        is_follower=False, account_owner=account,
        followers_count__gt=account.target_account_followers_count)
    counter = 0
    delete_target_accounts = []
    for user in target_accounts:
        try:
            tw_user = api.get_user(user.user_id)
        except tweepy.error.TweepError as err:
            if err.api_code == 50 or err.api_code == 63:
                logger.info("User {} not found or suspended!".format(
                    user.name))
                delete_target_accounts.append(user.user_id)
                BlackList.objects.get_or_create(user_id=user.user_id,
                                                reason="Not found/Suspended",
                                                account_owner=account)
                continue
            else:
                raise err

        if account.keywords:
            keyword_descr = _description_consist_keywords(account, tw_user)
            if not keyword_descr:
                delete_target_accounts.append(user.user_id)
                continue
        if tw_user and tw_user.followers_count > (
                account.target_account_followers_count):
            time.sleep(random.randrange(T_MIN, T_MAX))
            try:
                api.create_friendship(tw_user.id)
            except tweepy.error.TweepError as err:
                if err.api_code in [158, 160]:
                    logger.info(err.args[0][0]['message'])
                    user.is_follower = True
                    user.save(update_fields=('is_follower',))
                    continue
                else:
                    raise err
            try:
                _like_user_tweets(api, tw_user)
            except tweepy.error.TweepError as err:
                logger.info(err)
                continue

            logger.info("Follow %s", user)
            user.is_follower = True
            user.save(update_fields=('is_follower',))
            counter += 1
        else:
            delete_target_accounts.append(user.user_id)
            continue

        if counter == limit:
            logger.info("The limit of %s followings is reached", limit)
            break
    TargetTwitterAccount.objects.filter(
        user_id__in=delete_target_accounts, account_owner=account
    ).delete()


def _description_consist_keywords(account, tw_user):
    """Search keywords in twitter description"""
    keyword_descr = any(
        re.search('(^|\W){}($|\W)'.format(keyword),
                  tw_user.description.lower(), re.IGNORECASE)
        for keyword in account.keywords
    )
    return keyword_descr


def _like_user_tweets(api, tw_user):
    """Like tw_user's tweets that have likes more or equal LIKES_COUNT"""
    likes_limit = random.randrange(1, 4)
    liked_tweets = 0
    tweets = tw_user.timeline()[:10]  # get 10 latest tweets
    for t in tweets:
        try:
            if (t.favorite_count >= LIKES and not t.in_reply_to_status_id) or (
                    t.retweeted_status.favorite_count >= LIKES):
                api.create_favorite(t.id)
                liked_tweets += 1
        except tweepy.error.TweepError as err:
            logger.info(err.args[0][0]['message'])
            continue
        except AttributeError:
            continue
        if liked_tweets == likes_limit:
            break


def retweet():
    accounts = AccountOwner.objects.filter(is_active=True,
                                           retweet_func__isnull=False)
    for account in accounts:
        make_retweet = load_function(account.retweet_func)
        logger.info('Start retweeting for {}'.format(account))
        make_retweet(account)
        logger.info('Finish retweeting for {}'.format(account))


def retweet_verified_users_with_tag(user):
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
                    logger.info(err.args[0][0]['message'])
                    continue
            msg = 'New retweet for {}. Date: {}'.format(user, date.today())
            send_message_to_slack(msg)
            return


def retweet_verified_users(user):
    api = connect_to_twitter_api(user)
    max_retweets = _get_tweets_to_retweet(api)
    last_five_days_tweets = _get_retweeted_screen_names(api)

    for tweet in max_retweets:
        logger.info('Try to retweet tweet {} of {}'.format(
            tweet.id, tweet.user.screen_name))
        if tweet.user.screen_name not in last_five_days_tweets:
            try:
                api.retweet(tweet.id)
            except tweepy.error.TweepError as err:
                if err.api_code == 327 or err.api_code == 185:
                    logger.info(err.args[0][0]['message'])
                    continue
            msg = 'New retweet! Date: {}\ntwitter.com/{}/status/{}'.format(
                datetime.today().date(), tweet.user.screen_name, tweet.id)
            send_message_to_slack(msg)
            send_message_to_telegram(msg, user, False)
            return


def _get_retweeted_screen_names(api):
    """Return list of screen names of the already retweeted tweets
    for the last 5 days"""
    twitter_posts = api.me().timeline()
    last_five_days = datetime.today() - timedelta(days=5)
    last_five_days_tweets = [
        x.retweeted_status.user.screen_name for x in twitter_posts
        if x.created_at > last_five_days and x.retweeted is True
    ]
    return last_five_days_tweets


def _get_tweets_to_retweet(api):
    """Return sorted list of verified users tweets for the last day"""
    ver_users = VerifiedUserWithTag.objects.filter(
        account_owner__screen_name=api.me().screen_name
    )
    tweets_to_retweet = []
    last_tweet = datetime.today() - timedelta(days=1)
    for ver_user in ver_users:
        time.sleep(random.randrange(T_MIN, T_MAX))
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
    max_retweeted_tweets = sorted(tweets_to_retweet,
                                  key=lambda tw: tw.retweet_count,
                                  reverse=True)
    return max_retweeted_tweets


def make_unfollow_for_current_account(account):
    """Unfollow twitter accounts for current account owner"""
    logger.info('Start unfollow for {}'.format(account.screen_name))
    api = connect_to_twitter_api(account)
    following = api.me().friends_count
    _unfollow_accounts_not_followers(account, api)
    stats = get_count_of_followers_and_following(api)
    text = ("Finished unfollowing. Account: {}. Number of followers: {}."
            " We're following {}. Following before task: {}. Date: {}."
            .format(account.screen_name, *stats, following, date.today()))
    send_message_to_slack(text)
    send_message_to_telegram(text, account)
    logger.info(text)


def _unfollow_accounts_not_followers(account, api):
    """Unfollow accounts that are not following account owner"""
    limit = random.randrange(account.followers_limit - 10,
                             account.followers_limit)
    logger.info("The limit of unfollowing is set to %s", limit)
    count = 0
    not_in_followers = _get_following_list(account, api)
    for friend in reversed(not_in_followers):
        try:
            api.destroy_friendship(friend)
            time.sleep(random.randrange(T_MIN, T_MAX))
            user = api.get_user(friend)
            friendship = api.show_friendship(user.id, user.screen_name,
                                             api.me().id,
                                             api.me().screen_name)[0]
        except tweepy.error.TweepError as err:
            if err.api_code == 50 or err.api_code == 63:
                logger.info(err.args[0][0]['message'])
                continue
            else:
                raise err

        if friendship and not friendship.followed_by:
            logger.info("Unfollow {}".format(friend))
            try:
                BlackList.objects.create(user_id=friend, account_owner=account)
                TwitterFollower.objects.filter(
                    user_id=friend, account_owner=account).delete()
            except IntegrityError:
                logger.exception('Integrity Error during unfollowing')
                continue

        count += 1
        if count == limit:
            break


def _get_following_list(account, api):
    """Return the list of accounts ids that are followed by acc owner
    but not following current acc owner"""
    followers_list = api.followers_ids()
    friends_list = api.friends_ids()
    in_white_list = WhiteListTwitterUser.objects.filter(
        account_owner=account).values_list('user_id', flat=True)
    not_in_followers = [acc_id for acc_id in friends_list
                        if acc_id not in followers_list
                        and str(acc_id) not in in_white_list]
    return not_in_followers


def follow():
    accounts = AccountOwner.objects.filter(is_active=True)
    for account in accounts:
        try:
            make_follow_for_current_account(account)
            if account.follow_all_followers:
                follow_all_own_followers(account)
        except HTTPError:
            logger.exception('Something gone wrong')
        except tweepy.error.TweepError as err:
            message = err.args[0][0]['message']
            logger.info(message)
            if err.api_code in [89, 161, 226, 326]:
                send_message_to_slack(message)
                send_message_to_telegram(message, account, mode='HTML')
            else:
                logger.exception(err)
                raise err
        except Exception as err:
            logger.exception(err)
            raise err


def unfollow():
    accounts = AccountOwner.objects.filter(is_active=True)
    for account in accounts:
        try:
            make_unfollow_for_current_account(account)
        except HTTPError:
            logger.exception('Something gone wrong')
        except tweepy.error.TweepError as err:
            message = err.args[0][0]['message']
            logger.info(message)
            if err.api_code in [89, 226, 326]:
                send_message_to_slack(message)
                send_message_to_telegram(message, account)
            else:
                logger.exception(err)
                raise err
        except Exception as err:
            logger.exception(err)
            raise err


def follow_all_own_followers(account):
    logger.info('Start follow own followers for {}'.format(
        account.screen_name)
    )
    api = connect_to_twitter_api(account)
    count = _follow_followers(api)
    text = "Account: {}. Follow {} own followers." \
           " Date: {}".format(account.screen_name, count, date.today())
    send_message_to_slack(text)
    send_message_to_telegram(text, account)
    logger.info('Finish follow own followers for {}'.format(
        account.screen_name)
    )


def _follow_followers(api):
    """Follow twitter accounts that follow current twitter account owner"""
    count = 0
    not_in_friends = _get_followers_list(api)
    for follower in not_in_friends:
        time.sleep(random.randrange(T_MIN, T_MAX))
        try:
            api.create_friendship(follower)
        except tweepy.error.TweepError as err:
            if err.api_code == 50 or err.api_code == 63:
                logger.info(err.args[0][0]['message'])
                continue
            else:
                raise err
        logger.info("Follow %s", follower)
        count += 1
    return count


def _get_followers_list(api):
    """Return list of accounts ids that are following current acc owner but
    not followed by acc owner"""
    followers_list = api.followers_ids()
    friends_list = api.friends_ids()
    not_in_friends = [x for x in followers_list if x not in friends_list]
    return not_in_friends
