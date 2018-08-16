# Twitter bot

## Create your *Keys and Access Tokens*

Go to [Twitter Application Management](https://apps.twitter.com/) and click **"Create New App"**.  
Fill in the required fields on the website [https://apps.twitter.com/app/new](https://apps.twitter.com/app/new)  and click **"Yes, I have read and agree to the Twitter Developer Agreement."** then **"Create your Twitter application"**.  
Click **"Keys and Access Tokens"** and you look your *Consumer Key (API Key)* and *Consumer Secret (API Secret)*.  
Click **"create my access token"** and you give your *Access Token* and *Access Token Secret*.

## Usage
Use generated keys and tokens for Tweepy authentication in *`/twitterbot/bot/settings.py`*.

You can add users for twitter automation in **`TWITTER_ACCOUNT_SETTINGS`** in the same file.

You can specify an automation strategy individually for each user.
### Example

```
    'testuser': {
        'unfollow': ['utils.twitterbot.make_unfollow_for_current_account'],
        'follow': ['utils.twitterbot.make_follow_for_current_account',
                   'utils.twitterbot.follow_all_own_followers'],
        'followers_limit': 50,
        'retweet': True
    },
```
* *`'unfollow': [...]`* - a list of functions for unfollowing
* *`'follow': [...]`* - a list of functions for following
* *`'followers_limit': 10`* - a number for limit followers and unfollowers for current account
* *`'retweet': True`* - bool value, if True - make retweets for current account
###### Note
If you want to follow all the users who follows you - use the function `follow_all_own_followers()` in *`twitterbot/utils/twitterbot.py`*.
## Optional features
**Twitter bot** uses [celery tasks](http://docs.celeryproject.org/en/latest/userguide/tasks.html) for making the operations:
* follow users
* unfollow users
* retweet by a tag

However, you can also do this stuff with [django-admin commands](https://docs.djangoproject.com/en/2.1/howto/custom-management-commands/) in *`/twitterbot/management/commands`*.