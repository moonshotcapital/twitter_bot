import logging
import os
import csv
import tempfile
import tweepy
import requests
from datetime import date
from django.conf import settings

from requests.exceptions import HTTPError
from twitterbot.models import TwitterFollower, AccountOwner
from utils.common import (
    connect_to_twitter_api,
    get_poll_updates,
    replace_characters,
    send_poll_to_telegram,
    send_message_to_telegram,
    send_message_to_slack
)
from utils.get_followers_and_friends import get_accounts
from itertools import groupby

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_twitter_followers_list():
    tw_accounts = AccountOwner.objects.filter(is_active=True)
    for account in tw_accounts:
        try:
            api = connect_to_twitter_api(account)
            current_user = api.me()

            all_users_list = []
            for user_type in TwitterFollower.USER_TYPE_CHOICES:
                user_type = user_type[0]

                accounts_list = get_accounts(current_user, user_type)
                all_users_list.extend(accounts_list)
                db_list = TwitterFollower.objects.filter(
                    user_type=user_type, account_owner=account
                ).values('user_id', 'screen_name')

                # add new friends and followers to db after automation
                # marketing
                update_db_lists(accounts_list, account, user_type, db_list)

                # sync db if someone unsubscribed from us or etc.
                update_db_lists_non_automatic_changes(
                    accounts_list, account, user_type, db_list, current_user)

                if account.csv_statistic and (
                    user_type == TwitterFollower.FOLLOWER
                ):
                    send_csv_statistic_to_telegram(accounts_list, account,
                                                   'followers')
                    users_list = [next(obj) for i, obj in groupby(
                        sorted(all_users_list, key=lambda x: x.id_str),
                        lambda x: x.id_str)]
                    update_favourites_list(users_list, account)
        except (tweepy.error.TweepError, HTTPError):
            logger.exception('Something gone wrong')
            continue


def update_db_lists_non_automatic_changes(
        accounts_list, acc_owner, user_type, db_list, tw_user):
    db_users = [user['user_id'] for user in db_list]

    tw_list = [acc.id_str for acc in accounts_list]
    lost_accounts = [acc for acc in db_users if acc not in tw_list]
    TwitterFollower.objects.filter(
        user_id__in=lost_accounts,
        user_type=user_type,
        account_owner=acc_owner
    ).delete()

    if user_type == TwitterFollower.FOLLOWER:
        new_followers = [f for f in accounts_list if f.id_str not in db_users]
        new_followers = sorted(new_followers, key=lambda f: f.followers_count,
                               reverse=True)
        titles = '[{}]({})\nLocation: {}\nFollowers: {}, Friends: {}\n' \
                 '\U0000270F: {}\n'

        new_followers_info = [
            titles.format(
                u.screen_name, 'twitter.com/{}'.format(u.screen_name),
                replace_characters(u.location, '\n*_`'), u.followers_count,
                u.friends_count, replace_characters(u.description, '\n*_`')
            ) for u in new_followers
            ]
        stats = tw_user.followers_count, tw_user.friends_count
        text = ('New Twitter Followers Report!\n'
                '\U00002705{}  \U0000274C{}  \U00002B06{}\n'
                'Date: {}\nFollowers: {}, Friends: {}\n\n').format(
            len(new_followers), len(lost_accounts),
            len(new_followers) - len(lost_accounts), date.today(), *stats
        )
        text += '\n'.join(new_followers_info)

        # avoid telegram markdown errors
        send_message_to_telegram(text, acc_owner, mode='Markdown')
        send_message_to_slack(text)

        # send poll to add followers to favourites
        acc_names = [', '.join([acc.screen_name, str(acc.followers_count)])
                     for acc in new_followers]
        send_poll_to_telegram(acc_owner, acc_names)


def update_db_lists(accounts_list, acc_owner, user_type, db_list):

    db_user_ids = [user['user_id'] for user in db_list]
    accounts_list_to_add = [fr for fr in accounts_list
                            if fr.id_str not in db_user_ids]
    for account in accounts_list_to_add:
        account_info = {
            'user_id': account.id,
            'name': account.name,
            'screen_name': account.screen_name,
            'followers_count': account.followers_count,
            'user_type': user_type,
            'location': account.location
        }
        TwitterFollower.objects.create(account_owner=acc_owner, **account_info)

    # check if user change the screen name
    db_user_names = [user['screen_name'] for user in db_list]
    accounts_list_to_update = [fr for fr in accounts_list
                               if fr.screen_name not in db_user_names
                               and fr not in accounts_list_to_add]
    for account in accounts_list_to_update:
        TwitterFollower.objects.filter(
            user_id=account.id, user_type=user_type, account_owner=acc_owner
        ).update(screen_name=account.screen_name)


def send_csv_statistic_to_telegram(followers_list, acc_owner, filename):

    filename += '.csv'
    file_path = os.path.join(tempfile.gettempdir(), filename)
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
                [count, follower.screen_name, follower.name, follower.location,
                 follower.description, follower.followers_count,
                 follower.friends_count, start_follow]
            )

    token = settings.TELEGRAM_NOTIFICATIONS_TOKEN
    url = "https://api.telegram.org/bot{}/sendDocument".format(token)
    r = requests.post(url, data={'chat_id': acc_owner.telegram_chat_id},
                      files={'document': open(file_path, 'r')})
    r.raise_for_status()


def update_favourites_list(users_list, account):
    logger.info('Started updating favourites list!')

    favourites = []
    updates = get_poll_updates(account).json()['result']
    for upd in updates:
        try:
            options = upd['poll']['options']
            for opt in options:
                if opt['voter_count'] > 0:
                    acc_name = opt['text'].split(',')[0]
                    favourites.append(acc_name)
        except KeyError:
            continue
    favourites = set(favourites)
    TwitterFollower.objects.filter(
        screen_name__in=favourites, account_owner=account
    ).update(is_favourite=True)

    # send csv statistic
    db_favourites = TwitterFollower.objects.filter(
        is_favourite=True, account_owner=account
    ).values_list('user_id', flat=True)

    favourites_list = [f for f in users_list if f.id_str in db_favourites]
    favourites_list_print = [
        '[{}]({}), {}'.format(
            u.screen_name, 'twitter.com/{}'.format(u.screen_name),
            u.followers_count) for u in favourites_list
    ]

    text = 'Favourites list!\n\n' + '\n'.join(favourites_list_print)
    send_message_to_telegram(text, account, mode='Markdown')
    send_csv_statistic_to_telegram(favourites_list, account, 'favourites')
    logger.info('Finished updating favourites list!')
