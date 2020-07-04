import logging
from twitterbot.models import TwitterFollower

logger = logging.getLogger(__name__)


def get_accounts(twitter_user, user_type):
    logger.info('Start process of getting {} for {}'.format(
        user_type, twitter_user.screen_name))

    if user_type in ['followers', TwitterFollower.FOLLOWER]:
        tw_list = twitter_user.followers
        tw_accounts_count = twitter_user.followers_count
    elif user_type in ['friends', TwitterFollower.FRIEND]:
        tw_list = twitter_user.friends
        tw_accounts_count = twitter_user.friends_count
    else:
        logger.info("{} is not valid user_type. "
                    "Pls choose 'followers' or 'friends'".format(user_type))
        return

    tw_accounts_list = tw_list(cursor=-1, count=200)
    accounts = tw_accounts_list[0]
    accounts_count = len(tw_accounts_list[0])
    next_cursor = tw_accounts_list[1][1]

    # followers for one rate limit window = 3000

    while accounts_count < tw_accounts_count:
        tw_accounts_list = tw_list(cursor=next_cursor, count=200)
        accounts += tw_accounts_list[0]
        accounts_count += len(tw_accounts_list[0])
        next_cursor = tw_accounts_list[1][1]
        if next_cursor == 0:
            break
    logger.info('Finish process of getting followers '
                'for {}'.format(twitter_user.screen_name))
    return accounts
