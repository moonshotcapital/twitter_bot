from django.contrib import admin
from .models import (
    AccountOwner,
    BlackList,
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


admin.site.register(BlackList)
admin.site.register(WhiteListTwitterUser)
admin.site.register(AccountOwner)
