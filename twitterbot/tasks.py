import tweepy

from celery import task
from celery.utils.log import get_task_logger
from datetime import timedelta, datetime
from django.conf import settings
from django.utils import timezone
from twitterbot.models import AccountOwner, RunTasksTimetable, TwitterFollower
import random
from utils.get_followers_and_friends import get_accounts
from utils.common import (connect_to_twitter_api, save_twitter_users_to_db,
                          load_function)
from utils.sync_followers import update_twitter_followers_list

logger = get_task_logger(__name__)


@task
def update_followers_list_task():
    logger.info('Started updating followers list!')
    update_twitter_followers_list()
    logger.info('Finished updating followers list!')


@task
def create_timetable():
    """
    Create everyday timetable for main actions: follow, unfollow, retweet
    """
    logger.info('Started creating tasks timetable')
    start = timezone.now()
    tasks = {
        'follow': random.randrange(
            int(settings.FOLLOW_TASK_MAX_TIME_PER_DAY) - 2,
            int(settings.FOLLOW_TASK_MAX_TIME_PER_DAY)
        ),
        'unfollow': random.randrange(
            int(settings.FOLLOW_TASK_MAX_TIME_PER_DAY) - 3,
            int(settings.FOLLOW_TASK_MAX_TIME_PER_DAY) - 1
        ),
        'retweet': int(settings.RETWEET_TASK_MAX_TIME_PER_DAY)
    }
    actions, task_list = [], []
    [actions.extend([action_name]*tasks[action_name]) for action_name in tasks]
    random.shuffle(actions)
    activity_hours = datetime.max.hour - start.hour
    max_gap_in_minutes = int(activity_hours / len(actions) * 60)
    for action_name in actions:
        start = start + timedelta(
            minutes=random.randrange(60, max_gap_in_minutes),
            seconds=random.randrange(1, 60)
        )
        task_list.append(
            RunTasksTimetable(name=action_name, execution_time=start)
        )
    RunTasksTimetable.objects.bulk_create(task_list)
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
