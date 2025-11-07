from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User


class Command(BaseCommand):
    help = 'Create necessary user groups and permissions'

    def handle(self, *args, **kwargs):
        admin_groups_entries = [
            {"name": "admin"},
            {"name": "user"},
        ]
        if not Group.objects.exists():
            for index, entry in enumerate(admin_groups_entries):
                group, success = Group.objects.get_or_create(**entry)
                if entry['name'] == 'admin':
                    users = User.objects.filter(is_superuser=True)
                    for user in users:
                        user.groups.add(group)
                        user.save()
                if index == 0:
                    all_permission = Permission.objects.all()
                    group.permissions.set(all_permission)
                else:
                    view_permissions = Permission.objects.filter(codename__startswith='view_')
                    group.permissions.set(view_permissions)
        else:
            self.stdout.write("There was data on auth group.")
        self.stdout.write('Done!')
