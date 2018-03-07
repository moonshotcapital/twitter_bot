from django.contrib import admin
from .models import TwitterUser, Followers, TargetTwitterAccounts, BlackList

admin.site.register(TwitterUser)
admin.site.register(Followers)
admin.site.register(TargetTwitterAccounts)
admin.site.register(BlackList)
