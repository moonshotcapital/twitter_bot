import tweepy
import time

from celery import task
from celery.utils.log import get_task_logger
from datetime import timedelta
from django.utils import timezone
from twitterbot.models import AccountOwner, RunTasksTimetable, TwitterFollower
import random
from utils.get_followers_and_friends import get_accounts
from utils.common import (connect_to_twitter_api, save_twitter_users_to_db,
                          load_function)
from utils.sync_followers import (
    update_twitter_followers_list,
    update_favourites_list
)

logger = get_task_logger(__name__)


@task
def update_followers_list_task():
    logger.info('Started updating followers list!')
    update_twitter_followers_list()
    logger.info('Finished updating followers list!')


@task
def update_favourites_list_task():
    logger.info('Started updating favourites list!')
    update_favourites_list()
    logger.info('Finished updating favourites list!')


@task
def create_timetable():
    logger.info('Started creating tasks timetable')
    time.sleep(random.randrange(10, 30))
    start = timezone.now()
    # Scheduler task executes at 7 a.m. everyday
    # And all the modules will execute after this task in time 'time_execute'
    # Create time list from 7 a.m. to 22 p.m.
    hours_range = list(range(0, 15))
    random.shuffle(hours_range)
    tasks = {'follow': random.randrange(4, 6),
             'unfollow': random.randrange(3, 5),
             'retweet': 3}
    for task_name in tasks:
        for x in range(tasks[task_name]):
            hours_execute = hours_range.pop()
            time_execute = start + timedelta(hours=hours_execute,
                                             minutes=random.randrange(60))
            RunTasksTimetable.objects.create(name=task_name,
                                             execution_time=time_execute)
    logger.info('New timetable created for {}'.format(start.date()))


@task
def run_tasks():
    logger.info('Check tasks to execute')
    # Scheduler task executes every 2 minutes
    last_check = timezone.now() - timedelta(minutes=2)
    action_list = RunTasksTimetable.objects.filter(
        execution_time__lt=timezone.now(),
        execution_time__gt=last_check, executed=False)
    for action in action_list:
        path = 'utils.twitterbot.' + action.name
        func = load_function(path)
        try:
            logger.info('Try execute {} task'.format(action.name))
            func()
        except:
            logger.info('Some errors detected. Check logs for more info.')
            action.failed = True
            action.save(update_fields=('failed',))
            continue
        finally:
            action.executed = True
            action.save(update_fields=('executed',))
    logger.info('Finished checking tasks to execute')


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
        followers = get_accounts(twitter_user, TwitterFollower.FOLLOWER)

        try:
            save_twitter_users_to_db(followers, acc_owner)
            logger.info('Successfully loaded followers of {}'.format(user))
        except tweepy.error.TweepError as err:
            raise err

        if options['friends']:
            logger.info('Loading friends of {}'.format(user))
            friends = get_accounts(twitter_user, TwitterFollower.FRIEND)

            try:
                save_twitter_users_to_db(friends, acc_owner)
                logger.info('Successfully loaded friends of {}'
                                       .format(user))
            except tweepy.error.TweepError as err:
                raise err
