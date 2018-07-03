import tweepy

from celery import task
from celery.utils.log import get_task_logger

from twitterbot.models import AccountOwner
from utils.get_followers_and_friends import get_followers, get_friends
from utils.common import connect_to_twitter_api, save_twitter_users_to_db
from utils.twitterbot import follow, retweet_verified_users, unfollow
from utils.sync_followers import update_twitter_followers_list

logger = get_task_logger(__name__)

@task
def follow_people():
    logger.info('Started following people!')
    follow()
    logger.info('Finished following people!')


@task
def update_followers_list_task():
    logger.info('Started updating followers list!')
    update_twitter_followers_list()
    logger.info('Finished updating followers list!')


@task
def retweet_task():
    logger.info('Started retweeting!')
    retweet_verified_users()
    logger.info('Finished retweeting!')


@task
def unfollow_users_task():
    logger.info('Started unfollowing users!')
    unfollow()
    logger.info('Finished unfollowing users!')


@task
def get_followers_and_friends_task(options):
    account_owner = options['account_owner'][0]
    acc_owner = AccountOwner.objects.get(
        is_active=True, screen_name=account_owner)
    if acc_owner:
        api = connect_to_twitter_api(acc_owner)
    else:
        logger.info('Can not find account owner with screen'
                    ' name: {}'.format(account_owner))
        return

    for user in options['username']:
        logger.info('Loading followers of {}'.format(user))
        twitter_user = api.get_user(user)
        followers = get_followers(twitter_user)

        try:
            save_twitter_users_to_db(followers, acc_owner)
            logger.info('Successfully loaded followers of {}'.format(user))
        except tweepy.error.TweepError as err:
            raise err

        if options['friends']:
            logger.info('Loading friends of {}'.format(user))
            friends = get_friends(twitter_user)

            try:
                save_twitter_users_to_db(friends, acc_owner)
                logger.info('Successfully loaded friends of {}'
                                       .format(user))
            except tweepy.error.TweepError as err:
                raise err
