from django.contrib import admin
from .models import Country, Duty, Group, Institute, Member, MemberDuty, MembershipPeriod, AuthorshipPeriod, AuthorDetails, DutyType, AuthorInstituteAffiliation, ActiveDutyManager, Category, CommonFound


class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'surname']  # Fields to display in the list view
    search_fields = ['name', 'surname']  # Fields to search by
    list_filter = ['name', 'surname']


class InstituteAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']

class DutyAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']

class GroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']

class MemberDutyAdmin(admin.ModelAdmin):
    list_display = ['member']
    search_fields = ['member__name']
    list_filter = ['member']
class MembershipPeriodAdmin(admin.ModelAdmin):
    list_display = ['member', 'institute', 'start_date', 'end_date']
    search_fields = ['member__name', 'institute__name', 'start_date', 'end_date']
    list_filter = ['member','institute', 'start_date', 'end_date']
class AuthorshipPeriodAdmin(admin.ModelAdmin):
    list_display = ['member', 'start_date', 'end_date']
    search_fields = ['member__name', 'start_date', 'end_date']
    list_filter = ['member','start_date', 'end_date']

class AuthorDetailsAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'member']
    search_fields = ['author_name', 'member__name', 'member__surname']
    list_filter = ['member']  # Filter by related member

class CommonFoundAdmin(admin.ModelAdmin):
    list_display = ['member', 'start_date', 'end_date']
    search_fields = ['member__name', 'start_date', 'end_date']
    list_filter = ['member','start_date', 'end_date']

class AuthorInstituteAffiliationAdmin(admin.ModelAdmin):
    list_display = ['get_member_name', 'institute', 'order', 'creation_date', 'end_date']
    search_fields = ['author_details__member__name', 'institute__name', 'order', 'creation_date', 'end_date']
    list_filter = ['author_details__member', 'order', 'institute', 'creation_date', 'end_date']

    def get_member_name(self, obj):
        return f"{obj.author_details.member.name} {obj.author_details.member.surname}"
    get_member_name.short_description = 'Member'


# Register your models here.
admin.site.register(Country)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Institute, InstituteAdmin)
admin.site.register(Duty, DutyAdmin)
admin.site.register(Member, MemberAdmin)
admin.site.register(MemberDuty, MemberDutyAdmin)
admin.site.register(MembershipPeriod, MembershipPeriodAdmin)
admin.site.register(AuthorshipPeriod, AuthorshipPeriodAdmin)
admin.site.register(AuthorInstituteAffiliation, AuthorInstituteAffiliationAdmin)
admin.site.register(AuthorDetails, AuthorDetailsAdmin)  
admin.site.register(CommonFound, CommonFoundAdmin)  

