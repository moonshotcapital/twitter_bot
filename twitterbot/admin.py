from django.contrib import admin
from .models import TwitterUser, TargetTwitterAccount, BlackList

admin.site.register(TwitterUser)
admin.site.register(TargetTwitterAccount)
admin.site.register(BlackList)
