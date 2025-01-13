from django.contrib import admin
from .models import Country, Duty, Group, Institute, Member, MemberDuty, MembershipPeriod, AuthorshipPeriod, AuthorDetails


class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'surname'] # Fields to display in the list view
    search_fields = ['name', 'surname']  # Fields to search by
    list_filter = ['name', 'surname']


# Register your models here.
admin.site.register(Country)
admin.site.register(Group)
admin.site.register(Institute)
admin.site.register(Duty)
admin.site.register(Member, MemberAdmin)
admin.site.register(MemberDuty)
admin.site.register(MembershipPeriod)
admin.site.register(AuthorshipPeriod)
admin.site.register(AuthorDetails)
