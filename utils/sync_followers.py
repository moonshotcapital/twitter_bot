import logging
import os
import csv
import tempfile
import requests
from django.conf import settings

from twitterbot.models import BlackList, TwitterFollower, AccountOwner
from utils.common import connect_to_twitter_api
from utils.get_followers_and_friends import get_followers, get_friends
from utils.twitterbot import send_message_to_telegram, send_message_to_slack

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TWITTER_ACCOUNT_SETTINGS = settings.TWITTER_ACCOUNT_SETTINGS


def update_twitter_followers_list():
    tw_accounts = AccountOwner.objects.filter(is_active=True)
    for account in tw_accounts:
        api = connect_to_twitter_api(account)
        current_user = api.me()
        friends_list = get_friends(current_user)
        followers_list = get_followers(current_user)

        # sync db if someone unsubscribed from us or etc.
        update_db_followers_list_due_to_non_automatic_changes(
            friends_list, followers_list, account)
        # add new friends and followers to db after automation marketing
        update_db_friends_list(friends_list, account)
        update_db_followers_list(followers_list, account)
        send_csv_statistic_to_telegram(followers_list, account)


def update_db_followers_list_due_to_non_automatic_changes(friends_list,
                                                          followers_list,
                                                          acc_owner):
    db_followers = TwitterFollower.objects.filter(
        user_type=TwitterFollower.FOLLOWER, account_owner=acc_owner
    ).values_list('user_id', flat=True)

    tw_followers = [user.id_str for user in followers_list]
    lost_followers = [x for x in db_followers if x not in tw_followers]
    TwitterFollower.objects.filter(
        user_id__in=lost_followers,
        user_type=TwitterFollower.FOLLOWER,
        account_owner=acc_owner
    ).delete()

    db_friends = TwitterFollower.objects.filter(
        user_type=TwitterFollower.FRIEND,
        account_owner=acc_owner
    ).values_list('user_id', flat=True)

    tw_friends = [user.id_str for user in friends_list]
    lost_friends = [x for x in db_friends if x not in tw_friends]
    TwitterFollower.objects.filter(
        user_id__in=lost_friends,
        user_type=TwitterFollower.FRIEND,
        account_owner=acc_owner
    ).delete()

    overall_followers_increase = len(followers_list) - len(db_followers)

    text = 'Followers report! Lost: {}. Increase: {}. Overall increase: {}' \
           ''.format(len(lost_followers),
                     overall_followers_increase + len(lost_followers),
                     overall_followers_increase
                     )
    send_message_to_telegram(text, acc_owner)
    send_message_to_slack(text)


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


def send_csv_statistic_to_telegram(followers_list, acc_owner):
    allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(acc_owner.screen_name)

    if 'csv_statistic' in allowed_actions:
        file_path = os.path.join(tempfile.gettempdir(), 'followers.csv')
        f = open(file_path, 'w')
        file_writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
        file_header = ['#', 'twitter name', 'name', 'location', 'description',
                       'followers count', 'friends count', 'start following']
        file_writer.writerow(file_header)

        followers = TwitterFollower.objects.filter(
            account_owner=acc_owner, user_type=TwitterFollower.FOLLOWER
        ).values('screen_name', 'created')
        start_follow_list = {
            x.get('screen_name'): x.get('created').date() for x in followers
        }
        for count, follower in enumerate(followers_list, 1):
            start_follow = start_follow_list.get(follower.screen_name)
            file_writer.writerow(
                [count, follower.screen_name, follower.name, follower.location,
                 follower.description, follower.followers_count,
                 follower.friends_count, start_follow]
            )
        f.close()

        token = settings.TELEGRAM_NOTIFICATIONS_TOKEN
        url = "https://api.telegram.org/bot{}/sendDocument".format(token)
        r = requests.post(url, data={'chat_id': acc_owner.telegram_chat_id},
                          files={'document': open(file_path, 'r')})
        r.raise_for_status()
