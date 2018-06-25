import logging
from django.core.management.base import BaseCommand
from django.conf import settings

import tweepy

from twitterbot.models import TargetTwitterAccount, BlackList, AccountOwner
from utils.get_followers_and_friends import get_followers, get_friends

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


class Command(BaseCommand):

    help = 'Loads followers for given twitter user ' \
           'and saves them to DB (TargetTwitterAccount table)'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)
        parser.add_argument('account_owner', nargs='+', type=str)

        parser.add_argument(
            '--include-friends',
            action="store_true",
            dest='friends',
            default=False,
            help='Additionally loads friends of twitter user'
        )

    @staticmethod
    def save_twitter_users_to_db(twitter_users, acc_owner):
        for tw_user in twitter_users:
            follower_exist = TargetTwitterAccount.objects.filter(
                user_id=tw_user.id, account_owner=acc_owner
            ).exists()

            exist_in_black_list = BlackList.objects.filter(
                user_id=tw_user.id, account_owner=acc_owner
            ).exists()

            if not follower_exist and not exist_in_black_list:
                follower_info = {
                    'user_id': tw_user.id,
                    'name': tw_user.name,
                    'screen_name': tw_user.screen_name,
                    'followers_count': tw_user.followers_count,
                    'location': tw_user.location
                }
                TargetTwitterAccount.objects.create(**follower_info,
                                                    account_owner=acc_owner)
                logger.info("Save %s", tw_user.name)
            else:
                logger.info("Skipped %s", tw_user.name)
                continue

    def handle(self, *args, **options):
        account_owner = options['account_owner'][0]
        acc_owner = AccountOwner.objects.get(
            is_active=True, screen_name=account_owner)
        if acc_owner:
            consumer_key = acc_owner.consumer_key
            consumer_secret = acc_owner.consumer_secret
            access_token = acc_owner.access_token
            access_token_secret = acc_owner.access_token_secret
        else:
            self.stdout.write(
                self.style.ERROR('Can not find account owner with screen'
                                 ' name: {}'.format(account_owner)))
            return

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)

        for user in options['username']:

            self.stdout.write('Loading followers of {}'.format(user))
            twitter_user = api.get_user(user)
            followers = get_followers(twitter_user)

            try:
                self.save_twitter_users_to_db(followers, acc_owner)
                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded followers of {}'
                                       .format(user)))
            except tweepy.error.TweepError as err:
                raise err

            if options['friends']:
                self.stdout.write('Loading friends of {}'.format(user))
                friends = get_friends(twitter_user)

                try:
                    self.save_twitter_users_to_db(friends, acc_owner)
                    self.stdout.write(
                        self.style.SUCCESS('Successfully loaded friends of {}'
                                           .format(user)))
                except tweepy.error.TweepError as err:
                    raise err
