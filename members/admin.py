from django.contrib import admin
from .models import Country, Duty, Group, Institute, Member, MemberDuty, MembershipPeriod, AuthorshipPeriod, AuthorDetails


class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'surname']  # Fields to display in the list view
    search_fields = ['name', 'surname']  # Fields to search by
    list_filter = ['name', 'surname']


class InstituteAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']


class AuthorDetailsAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'member']
    search_fields = ['author_name', 'member__name', 'member__surname']
    list_filter = ['member']  # Filter by related member


# Register your models here.
admin.site.register(Country)
admin.site.register(Group)
admin.site.register(Institute, InstituteAdmin)
admin.site.register(Duty)
admin.site.register(Member, MemberAdmin)
admin.site.register(MemberDuty)
admin.site.register(MembershipPeriod)
admin.site.register(AuthorshipPeriod)
admin.site.register(AuthorDetails, AuthorDetailsAdmin)
