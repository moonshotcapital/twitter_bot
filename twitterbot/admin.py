from django.contrib import admin
from .models import (
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
    list_display = ('screen_name', 'tags')


admin.site.register(TargetTwitterAccount)
admin.site.register(BlackList)
admin.site.register(WhiteListTwitterUser)
