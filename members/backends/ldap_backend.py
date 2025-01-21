from django.contrib.auth.models import Group
from django_auth_ldap.backend import LDAPBackend


class CustomLDAPBackend(LDAPBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username and '@' in username:
            username = username.split('@')[0] # Strip domain part

        user = super().authenticate(request, username, password, **kwargs)

        if user is not None:
            # Fetch LDAP groups associated with the user
            ldap_groups = user.ldap_user.group_names
            self.assign_local_groups(user, ldap_groups)
        return user

    def assign_local_groups(self, user, ldap_groups):
        """Assign the local groups based on LDAP group memberships."""
        if 'lst-membership-admin' in ldap_groups:
            admin_group = Group.objects.get(name='admin')
            user.groups.add(admin_group)
            user.is_staff = True
            user.is_superuser = True
            user.save()
        elif 'lst-sapo' in ldap_groups:
            user_group = Group.objects.get(name='sapo')
            user.groups.add(user_group)
        elif 'lst-members' in ldap_groups:
            user_group = Group.objects.get(name='user')
            user.groups.add(user_group)

        user.save()
