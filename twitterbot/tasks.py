from celery import task
from celery.utils.log import get_task_logger
from utils.twitterbot import main
from utils.get_friends_list import update_followers_list

logger = get_task_logger(__name__)

@task
def follow_people():
    logger.info('Started following people!')
    main()
    logger.info('Finished following people!')


@task
def update_followers_list_task():
    logger.info('Started updating followers list!')
    update_followers_list()
    logger.info('Finished updating followers list!')
