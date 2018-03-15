from celery import task
from celery.utils.log import get_task_logger
from utils.twitterbot import main

logger = get_task_logger(__name__)

@task
def follow_people():
    logger.info('Started following people!')
    main()
    logger.info('Finished following people!')

