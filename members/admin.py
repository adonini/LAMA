from django.contrib import admin
from .models import ActiveDutyManager, Country, Duty, Group, Institute, Member, MemberDuty
# Register your models here.
admin.site.register(Country)
admin.site.register(Group)
admin.site.register(Institute)
admin.site.register(Duty)
admin.site.register(Member)
admin.site.register(MemberDuty)