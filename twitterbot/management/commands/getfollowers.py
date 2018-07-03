import logging
from django.core.management.base import BaseCommand

from twitterbot.tasks import get_followers_and_friends_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def handle(self, *args, **options):
        self.stdout.write('Start process')
        get_followers_and_friends_task.delay(options)
        self.stdout.write('Process is executed in async mode. Enjoy!')
