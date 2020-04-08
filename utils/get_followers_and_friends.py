import logging


logger = logging.getLogger(__name__)


def get_followers(twitter_user):
    logger.info('Start process of getting followers '
                'for {}'.format(twitter_user.screen_name))
    followers = []
    followers_count = 0

    tw_followers_list = twitter_user.followers(cursor=-1, count=200)
    followers += tw_followers_list[0]
    followers_count += len(tw_followers_list[0])
    next_cursor = tw_followers_list[1][1]

    # followers for one rate limit window = 3000

    while followers_count < twitter_user.followers_count:
        tw_followers_list = twitter_user.followers(cursor=next_cursor,
                                                   count=200)
        followers += tw_followers_list[0]
        followers_count += len(tw_followers_list[0])
        next_cursor = tw_followers_list[1][1]
        if next_cursor == 0:
            break
    logger.info('Finish process of getting followers '
                'for {}'.format(twitter_user.screen_name))
    return followers


def get_friends(twitter_user):
    logger.info('Start process of getting friends '
                'for {}'.format(twitter_user.screen_name))
    friends = []
    friends_count = 0

    tw_friends_list = twitter_user.friends(cursor=-1, count=200)
    friends += tw_friends_list[0]
    friends_count += len(tw_friends_list[0])
    next_cursor = tw_friends_list[1][1]

    # friends for one rate limit window = 3000

    while friends_count < twitter_user.friends_count:
        tw_friends_list = twitter_user.friends(
            cursor=next_cursor,
            count=200
        )
        friends += tw_friends_list[0]
        friends_count += len(tw_friends_list[0])
        next_cursor = tw_friends_list[1][1]
        if next_cursor == 0:
            break
    logger.info('Finish process of getting friends '
                'for {}'.format(twitter_user.screen_name))
    return friends
