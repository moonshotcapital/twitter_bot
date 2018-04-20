import logging

import tweepy
from django.conf import settings

from twitterbot.models import BlackList, TwitterFollower

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


def update_followers_list():

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)

    friends_list = api.friends()
    followers_list = api.followers()

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
            TwitterFollower.objects.delete(user_id=friend.id)
        else:
            continue

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
            TwitterFollower.objects.delete(user_id=follower.id)
        else:
            continue
