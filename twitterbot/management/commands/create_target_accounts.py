from django.core.management.base import BaseCommand
import logging
from utils.common import save_twitter_users_to_db, connect_to_twitter_api
from utils.get_followers_and_friends import get_accounts
from twitterbot.models import AccountOwner, TwitterFollower

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Loads followers and friends of accounts that current user follows 
              and saves them to DB (TargetTwitterAccount table)'''

    def add_arguments(self, parser):
        parser.add_argument('account_owner', nargs='+', type=str)

    def handle(self, *args, **options):
        self.stdout.write('Start process')
        account_owner = options['account_owner'][0]
        try:
            acc_owner = AccountOwner.objects.get(
                is_active=True, screen_name=account_owner)
            api = connect_to_twitter_api(acc_owner)
            friends = get_accounts(api.me(), TwitterFollower.FRIEND)
            for friend in friends:
                target_accounts = get_accounts(friend, TwitterFollower.FRIEND)
                target_accounts += get_accounts(
                    friend, TwitterFollower.FOLLOWER)
                save_twitter_users_to_db(target_accounts, acc_owner)
        except:
            self.stdout.write('Account owner not found')
        self.stdout.write('Finish process!')
