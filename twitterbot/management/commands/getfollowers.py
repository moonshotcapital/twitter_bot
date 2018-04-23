import logging
from django.core.management.base import BaseCommand
from django.conf import settings

import tweepy

from twitterbot.models import TargetTwitterAccount

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

        parser.add_argument(
            '--include-friends',
            action="store_true",
            dest='friends',
            default=False,
            help='Additionally loads friends of twitter user'
        )

    def handle(self, *args, **options):

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)

        for user in options['username']:

            self.stdout.write('Loading followers of {}'.format(user))

            try:
                for page in tweepy.Cursor(api.followers_ids,
                                          screen_name=user).pages():
                    for follower_id in page:
                        follower = api.get_user(id=follower_id)
                        follower_exist = TargetTwitterAccount.objects.filter(
                            user_id=follower.id
                        ).exists()

                        if not follower_exist:
                            follower_info = {
                                'user_id': follower.id,
                                'name': follower.name,
                                'screen_name': follower.screen_name,
                                'followers_count': follower.followers_count,
                                'location': follower.location
                            }
                            TargetTwitterAccount.objects.create(**follower_info)
                            logger.info("Save %s", follower.name)
                        else:
                            logger.info("Skipped %s", follower.name)
                            continue

                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded followers of {}'
                                       .format(user)))

            except tweepy.error.TweepError as err:
                raise err

        if options['friends']:

            self.stdout.write('Loading friends of {}'.format(user))

            try:
                for page in tweepy.Cursor(api.friends_ids,
                                          screen_name=user).pages():
                    for friend_id in page:
                        friend = api.get_user(id=friend_id)
                        friend_exist = TargetTwitterAccount.objects.filter(
                            user_id=friend.id
                        ).exists()

                        if not friend_exist:
                            friend_info = {
                                'user_id': friend.id,
                                'name': friend.name,
                                'screen_name': friend.screen_name,
                                'followers_count': friend.followers_count,
                                'location': friend.location
                            }
                            TargetTwitterAccount.objects.create(**friend_info)
                            logger.info("Save %s", friend.name)
                        else:
                            logger.info("Skipped %s", friend.name)
                            continue

                self.stdout.write(
                    self.style.SUCCESS('Successfully loaded friends of {}'
                                       .format(user)))

            except tweepy.error.TweepError as err:
                raise err
