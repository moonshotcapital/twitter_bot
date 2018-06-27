from celery import task
from celery.utils.log import get_task_logger
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
