import logging

import tweepy
from django.conf import settings

from twitterbot.models import BlackList, TwitterFollower, AccountOwner
from utils.get_followers_and_friends import get_followers, get_friends

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


def update_twitter_followers_list():
    tw_accounts = AccountOwner.objects.filter(is_active=True)
    for account in tw_accounts:
        consumer_key = account.consumer_key
        consumer_secret = account.consumer_secret
        access_token = account.access_token
        access_token_secret = account.access_token_secret

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)

        current_user = api.me()
        friends_list = get_friends(current_user)
        followers_list = get_followers(current_user)

        # sync db if someone unsubscribed from us or etc.
        update_db_followers_list_due_to_non_automatic_changes(
            friends_list, followers_list, account)
        # add new friends and followers to db after automation marketing
        update_db_friends_list(friends_list, account)
        update_db_followers_list(followers_list, account)


def update_db_followers_list_due_to_non_automatic_changes(friends_list,
                                                          followers_list,
                                                          acc_owner):
    db_followers = TwitterFollower.objects.filter(
        user_type=TwitterFollower.FOLLOWER, account_owner=acc_owner
    ).values_list('user_id', flat=True)

    tw_followers = [user.id_str for user in followers_list]
    for db_follower in db_followers:
        if db_follower not in tw_followers:
            TwitterFollower.objects.filter(
                user_id=db_follower,
                user_type=TwitterFollower.FOLLOWER,
                account_owner=acc_owner
            ).delete()

    db_friends = TwitterFollower.objects.filter(
        user_type=TwitterFollower.FRIEND,
        account_owner=acc_owner
    ).values_list('user_id', flat=True)

    tw_friends = [user.id_str for user in friends_list]
    for db_friend in db_friends:
        if db_friend not in tw_friends:
            TwitterFollower.objects.filter(
                user_id=db_friend,
                user_type=TwitterFollower.FRIEND,
                account_owner=acc_owner
            ).delete()


def update_db_friends_list(friends_list, acc_owner):
    for friend in friends_list:
        user_type = TwitterFollower.FRIEND
        friend_exist = TwitterFollower.objects.filter(
            user_id=friend.id,
            user_type=user_type,
            account_owner=acc_owner
        ).exists()

        exist_in_black_list = BlackList.objects.filter(
            user_id=friend.id, account_owner=acc_owner
        ).exists()

        if not friend_exist and not exist_in_black_list:
            friends_info = {
                'user_id': friend.id,
                'name': friend.name,
                'screen_name': friend.screen_name,
                'followers_count': friend.followers_count,
                'user_type': user_type,
                'location': friend.location
            }
            TwitterFollower.objects.create(**friends_info,
                                           account_owner=acc_owner)
        elif friend_exist and exist_in_black_list:
            TwitterFollower.objects.filter(user_id=friend.id,
                                           account_owner=acc_owner).delete()
        else:
            continue


def update_db_followers_list(followers_list, acc_owner):
    for follower in followers_list:
        user_type = TwitterFollower.FOLLOWER
        follower_exist = TwitterFollower.objects.filter(
            user_id=follower.id,
            user_type=user_type,
            account_owner=acc_owner
        ).exists()
        exist_in_black_list = BlackList.objects.filter(
            user_id=follower.id, account_owner=acc_owner
        ).exists()
        if not follower_exist and not exist_in_black_list:
            follower_info = {
                'user_id': follower.id,
                'name': follower.name,
                'screen_name': follower.screen_name,
                'followers_count': follower.followers_count,
                'user_type': user_type,
                'location': follower.location
            }
            TwitterFollower.objects.create(**follower_info,
                                           account_owner=acc_owner)
        elif follower_exist and exist_in_black_list:
            TwitterFollower.objects.filter(user_id=follower.id,
                                           account_owner=acc_owner).delete()
        else:
            continue
