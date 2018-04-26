import logging

import tweepy
from django.conf import settings

from twitterbot.models import BlackList, TwitterFollower
from utils.get_followers_and_friends import get_followers, get_friends

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


def update_twitter_followers_list():

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)

    current_user = api.get_user('goformoonshot')
    friends_list = get_friends(current_user)
    followers_list = get_followers(current_user)

    # sync db if someone unsubscribed from us or etc.
    update_db_followers_list_due_to_non_automatic_changes(friends_list,
                                                          followers_list)
    # add new friends and followers to db after automation marketing
    update_db_friends_list(friends_list)
    update_db_followers_list(followers_list)


def update_db_followers_list_due_to_non_automatic_changes(friends_list,
                                                          followers_list):
    db_followers = TwitterFollower.objects.filter(
        user_type=TwitterFollower.FOLLOWER
    ).values_list('user_id', flat=True)

    for db_follower in db_followers:
        tw_foolowers = [user.id for user in followers_list]
        if db_follower not in tw_foolowers:
            TwitterFollower.objects.filter(
                user_id=db_follower,
                user_type=TwitterFollower.FOLLOWER
            ).delete()

    db_friends = TwitterFollower.objects.filter(
        user_type=TwitterFollower.FRIEND
    ).values_list('user_id', flat=True)

    for db_friend in db_friends:
        tw_friends = [user.id for user in friends_list]
        if db_friend not in tw_friends:
            TwitterFollower.objects.filter(
                user_id=db_friend,
                user_type=TwitterFollower.FRIEND
            ).delete()


def update_db_friends_list(friends_list):
    for friend in friends_list:
        user_type = TwitterFollower.FRIEND
        friend_exist = TwitterFollower.objects.filter(
            user_id=friend.id,
            user_type=user_type
        ).exists()

        exist_in_black_list = BlackList.objects.filter(
            user_id=friend.id
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
            TwitterFollower.objects.create(**friends_info)
        elif friend_exist and exist_in_black_list:
            TwitterFollower.objects.filter(user_id=friend.id).delete()
        else:
            continue


def update_db_followers_list(followers_list):
    for follower in followers_list:
        user_type = TwitterFollower.FOLLOWER
        follower_exist = TwitterFollower.objects.filter(
            user_id=follower.id,
            user_type=user_type
        ).exists()
        exist_in_black_list = BlackList.objects.filter(
            user_id=follower.id
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
            TwitterFollower.objects.create(**follower_info)
        elif follower_exist and exist_in_black_list:
            TwitterFollower.objects.filter(user_id=follower.id).delete()
        else:
            continue
