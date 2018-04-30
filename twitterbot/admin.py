from django.contrib import admin
from .models import TwitterFollower, TargetTwitterAccount, BlackList, Tag


@admin.register(TwitterFollower)
class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'screen_name', 'name', 'followers_count',
                    'user_type')


admin.site.register(TargetTwitterAccount)
admin.site.register(BlackList)
admin.site.register(Tag)
