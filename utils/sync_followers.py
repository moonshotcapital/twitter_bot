import logging
import os
import csv
import tempfile
import requests
from django.conf import settings

from twitterbot.models import TwitterFollower, AccountOwner
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
        update_db_lists_non_automatic_changes(friends_list, account,
                                              TwitterFollower.FRIEND)
        update_db_lists_non_automatic_changes(followers_list, account,
                                              TwitterFollower.FOLLOWER)

        # add new friends and followers to db after automation marketing
        update_db_lists(friends_list, account, TwitterFollower.FRIEND)
        update_db_lists(followers_list, account, TwitterFollower.FOLLOWER)

        send_csv_statistic_to_telegram(followers_list, account)


def update_db_lists_non_automatic_changes(accounts_list, acc_owner, user_type):
    db_list = TwitterFollower.objects.filter(
        user_type=user_type, account_owner=acc_owner
    ).values_list('user_id', flat=True)

    tw_list = [user.id_str for user in accounts_list]
    lost_accounts = [acc for acc in db_list if acc not in tw_list]
    TwitterFollower.objects.filter(
        user_id__in=lost_accounts,
        user_type=user_type,
        account_owner=acc_owner
    ).delete()

    if user_type == TwitterFollower.FOLLOWER:

        overall_followers_increase = len(accounts_list) - len(db_list)

        text = 'Followers report! Lost: {}. Increase: {}. Overall increase: ' \
               '{}'.format(len(lost_accounts),
                           overall_followers_increase + len(lost_accounts),
                           overall_followers_increase
                           )
        send_message_to_telegram(text, acc_owner)
        send_message_to_slack(text)


def update_db_lists(accounts_list, acc_owner, user_type):
    db_list_screen_names = TwitterFollower.objects.filter(
        user_type=user_type, account_owner=acc_owner
    ).values_list('screen_name', flat=True)
    accounts_list_to_add = [fr for fr in accounts_list
                            if fr.screen_name not in db_list_screen_names]

    for account in accounts_list_to_add:
        account_info = {
            'user_id': account.id,
            'name': account.name,
            'screen_name': account.screen_name,
            'followers_count': account.followers_count,
            'user_type': user_type,
            'location': account.location
        }
        TwitterFollower.objects.create(**account_info,
                                       account_owner=acc_owner)


def send_csv_statistic_to_telegram(followers_list, acc_owner):
    allowed_actions = TWITTER_ACCOUNT_SETTINGS.get(acc_owner.screen_name)

    if 'csv_statistic' in allowed_actions:
        file_path = os.path.join(tempfile.gettempdir(), 'followers.csv')
        with open(file_path, 'w') as f:
            f_writer = csv.writer(f, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            file_header = [
                '#', 'twitter name', 'name', 'location', 'description',
                'followers count', 'friends count', 'start following'
            ]
            f_writer.writerow(file_header)

            followers = TwitterFollower.objects.filter(
                account_owner=acc_owner, user_type=TwitterFollower.FOLLOWER
            ).values('screen_name', 'created')

            # create dict with {screen_name: join date} pairs
            start_follow_list = {x.get('screen_name'): x.get('created').date()
                                 for x in followers}

            for count, follower in enumerate(followers_list, 1):
                start_follow = start_follow_list.get(follower.screen_name)
                f_writer.writerow(
                    [count, follower.screen_name, follower.name,
                     follower.location, follower.description,
                     follower.followers_count, follower.friends_count,
                     start_follow]
                )

        token = settings.TELEGRAM_NOTIFICATIONS_TOKEN
        url = "https://api.telegram.org/bot{}/sendDocument".format(token)
        r = requests.post(url, data={'chat_id': acc_owner.telegram_chat_id},
                          files={'document': open(file_path, 'r')})
        r.raise_for_status()
