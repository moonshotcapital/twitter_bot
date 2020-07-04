import csv
import logging
from django.core.management.base import BaseCommand

from twitterbot.models import AccountOwner, TwitterFollower
from utils.common import connect_to_twitter_api
from utils.get_followers_and_friends import get_accounts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Loads followers for creating dataset in csv'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)

    def handle(self, *args, **options):
        self.stdout.write('Start process')
        tw_user = options['username'][0]
        account = AccountOwner.objects.filter(is_active=True).first()
        api = connect_to_twitter_api(account)
        tw_user = api.get_user(tw_user)
        followers = get_accounts(tw_user, TwitterFollower.FOLLOWER)
        folowers_with_a = [['@' + i.screen_name] for i in followers]

        file_name = "{}_followers.csv".format(tw_user.screen_name)
        with open("/home/ubuntu/{}".format(file_name), 'w') as file:
            wr = csv.writer(file)
            wr.writerows(folowers_with_a)
