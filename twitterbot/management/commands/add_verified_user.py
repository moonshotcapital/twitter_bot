from django.core.management.base import BaseCommand
import logging
from twitterbot.models import VerifiedUserWithTag, AccountOwner
from utils.common import connect_to_twitter_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Add user to the VerifiedUserWithTag table'''

    def add_arguments(self, parser):
        parser.add_argument('--screen_name', nargs='+', type=str)
        parser.add_argument('--account_owner', nargs='+', type=str)
        parser.add_argument('--tags', nargs='+', default='{}')

    def handle(self, *args, **options):
        self.stdout.write('Start process')
        screen_name = options['screen_name'][0]
        account_owner = options['account_owner'][0]
        tags = options['tags']
        try:
            acc_owner = AccountOwner.objects.get(
                is_active=True, screen_name=account_owner)
            api = connect_to_twitter_api(acc_owner)
            api.get_user(screen_name)
            VerifiedUserWithTag.objects.get_or_create(
                account_owner=acc_owner, screen_name=screen_name, tags=tags)
        except:
            self.stdout.write('Account owner or Verified user not found')
        self.stdout.write('Finish process!')
