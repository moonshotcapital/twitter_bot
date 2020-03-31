from django.contrib import admin
from .models import (
    AccountOwner,
    BlackList,
    RunTasksTimetable,
    TwitterFollower,
    TargetTwitterAccount,
    VerifiedUserWithTag,
    WhiteListTwitterUser
)


@admin.register(TwitterFollower)
class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'screen_name', 'name', 'followers_count',
                    'user_type')


@admin.register(VerifiedUserWithTag)
class VerifiedUserWithTagAdmin(admin.ModelAdmin):
    list_display = ('screen_name', 'tags', 'account_owner')


@admin.register(TargetTwitterAccount)
class TargetTwitterAccountAdmin(admin.ModelAdmin):
    list_display = ('screen_name', 'followers_count', 'location',
                    'is_follower', 'account_owner')


@admin.register(WhiteListTwitterUser)
class WhiteListTwitterUserAdmin(admin.ModelAdmin):
    list_display = ('screen_name', 'user_id', 'account_owner', 'created')


@admin.register(RunTasksTimetable)
class RunTasksTimetableAdmin(admin.ModelAdmin):
    list_display = ('name', 'execution_time', 'executed', 'failed', 'created')


admin.site.register(BlackList)
admin.site.register(AccountOwner)
