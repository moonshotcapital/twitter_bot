import logging

import tweepy
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from twitterbot.models import BlackList, TwitterFollower

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONSUMER_KEY = settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET
ACCESS_TOKEN = settings.ACCESS_TOKEN
ACCESS_TOKEN_SECRET = settings.ACCESS_TOKEN_SECRET


class Command(BaseCommand):

    help = 'Unfollow users by given screen_names or ids ' \
           'and move them to BlackList'

    def add_arguments(self, parser):
        # username can be changed to user_id
        parser.add_argument('username', nargs='*', type=str)

    def handle(self, *args, **options):

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                         wait_on_rate_limit_notify=True)

        if options['username']:
            # Unfollow current user or list of users given in manage.py command
            # example: python manage.py unfollow_user <username1> <username2>
            bad_users = options['username']
        else:
            # TODO: add logic for getting list of users for unfollowing process
            # list must contain screen_names or user_ids of Twitter User
            bad_users = TwitterFollower.objects.values_list('user_id',
                                                            flat=True)[:500]

        self.stdout.write('Start unfollowing users')
        for bad_user in bad_users:
            bad_user = api.get_user(bad_user)
            api.destroy_friendship(bad_user.id)

            # sync our db state due to unfollowing users
            try:
                BlackList.objects.create(user_id=bad_user.id)
                TwitterFollower.objects.filter(user_id=bad_user.id).delete()
            except IntegrityError:
                continue

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully unfollowed '
                    'from {}'.format(bad_user.screen_name)
                )
            )
