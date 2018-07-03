import importlib
import logging
import tweepy

from twitterbot.models import TargetTwitterAccount, BlackList

logger = logging.getLogger(__name__)


def load_function(function_path):
    """
    dynamically load a function from a string
    """

    func_data = function_path.split(".")
    module_path = ".".join(func_data[:-1])
    func_str = func_data[-1]

    module = importlib.import_module(module_path)

    return getattr(module, func_str)


def connect_to_twitter_api(account_owner):
    consumer_key = account_owner.consumer_key
    consumer_secret = account_owner.consumer_secret
    access_token = account_owner.access_token
    access_token_secret = account_owner.access_token_secret

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)
    return api


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
