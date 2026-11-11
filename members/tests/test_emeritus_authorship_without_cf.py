from datetime import date

import pytest
from django.contrib.auth.models import Group as AuthGroup, User
from django.core.management import call_command
from django.urls import reverse

from members.models import (
    Category,
    CommonFound,
    Duty,
    DutyType,
    Institute,
    Member,
    MemberDuty,
    MembershipPeriod,
)
from members.tests.helpers import assert_authorship_periods, assert_single_authorship_period
from members.views import recalculate_authorship_periods


def create_member(name='Emeritus', role='researcher'):
    return Member.objects.create(
        name=name,
        surname='Member',
        primary_email=f'{name.casefold()}@test.com',
        role=role,
    )


def create_institute():
    return Institute.objects.create(
        name='Emeritus Institute',
        long_name='Emeritus Test Institute',
    )


def create_duty(grants_authorship_without_cf=True, name='Emeritus status'):
    duty_type, _ = DutyType.objects.get_or_create(name='permanent')
    category, _ = Category.objects.get_or_create(name='Special')
    return Duty.objects.create(
        name=name,
        duty_type=duty_type,
        category=category,
        grants_authorship_without_cf=grants_authorship_without_cf,
    )


@pytest.mark.django_db
def test_emeritus_grants_exact_assignment_authorship_without_cf():
    member = create_member()
    MembershipPeriod.objects.create(
        member=member,
        institute=create_institute(),
        start_date=date(2024, 1, 1),
    )
    MemberDuty.objects.create(
        member=member,
        duty=create_duty(),
        start_date=date(2026, 3, 15),
        end_date=date(2027, 8, 31),
    )

    recalculate_authorship_periods(member)

    assert not CommonFound.objects.filter(member=member).exists()
    assert_single_authorship_period(member, date(2026, 3, 15), date(2027, 8, 31))


@pytest.mark.django_db
def test_emeritus_authorship_is_clipped_to_membership():
    member = create_member()
    MembershipPeriod.objects.create(
        member=member,
        institute=create_institute(),
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
    )
    MemberDuty.objects.create(
        member=member,
        duty=create_duty(),
        start_date=date(2026, 1, 1),
        end_date=date(2027, 12, 31),
    )

    recalculate_authorship_periods(member)

    assert_single_authorship_period(member, date(2026, 4, 1), date(2027, 3, 31))


@pytest.mark.django_db
def test_ending_open_emeritus_duty_ends_authorship(client):
    member = create_member()
    MembershipPeriod.objects.create(
        member=member,
        institute=create_institute(),
        start_date=date(2024, 1, 1),
    )
    assignment = MemberDuty.objects.create(
        member=member,
        duty=create_duty(),
        start_date=date(2026, 2, 10),
    )
    recalculate_authorship_periods(member)
    assert_single_authorship_period(member, date(2026, 2, 10), None)

    response = client.post(
        reverse('end_duty'),
        data={'id': assignment.id, 'end-date': '2026-11-10'},
    )

    assert response.status_code == 200
    assert response.json()['status'] == 'success'
    assignment.refresh_from_db()
    assert assignment.end_date == date(2026, 11, 10)
    assert_single_authorship_period(member, date(2026, 2, 10), date(2026, 11, 10))


@pytest.mark.django_db
def test_admin_can_see_end_button_for_open_emeritus_duty(client):
    user = User.objects.create_user(username='emeritus-admin', password='testpass')
    admin_group = AuthGroup.objects.create(name='admin')
    user.groups.add(admin_group)
    client.force_login(user)

    member = create_member()
    MembershipPeriod.objects.create(
        member=member,
        institute=create_institute(),
        start_date=date(2024, 1, 1),
    )
    assignment = MemberDuty.objects.create(
        member=member,
        duty=create_duty(),
        start_date=date(2026, 2, 10),
    )

    response = client.get(reverse('manage-member-pk', args=[member.id]))

    assert response.status_code == 200
    assert f'class="btn btn-sm btn-clear rounded-xl mt-0 endBtn" data-id="{assignment.id}"'.encode() in response.content


@pytest.mark.django_db
def test_regular_permanent_duty_still_requires_cf():
    member = create_member()
    MembershipPeriod.objects.create(
        member=member,
        institute=create_institute(),
        start_date=date(2024, 1, 1),
    )
    MemberDuty.objects.create(
        member=member,
        duty=create_duty(False, 'Regular Permanent Duty'),
        start_date=date(2026, 2, 10),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [])


@pytest.mark.django_db
def test_recalculation_command_updates_only_members_with_independent_duties():
    institute = create_institute()
    emeritus_member = create_member('CommandEmeritus')
    regular_member = create_member('CommandRegular')
    for member in (emeritus_member, regular_member):
        MembershipPeriod.objects.create(
            member=member,
            institute=institute,
            start_date=date(2024, 1, 1),
        )

    MemberDuty.objects.create(
        member=emeritus_member,
        duty=create_duty(),
        start_date=date(2026, 5, 1),
    )
    MemberDuty.objects.create(
        member=regular_member,
        duty=create_duty(False, 'Another Permanent Duty'),
        start_date=date(2026, 5, 1),
    )

    call_command('recalculate_authorship_without_cf')

    assert_single_authorship_period(emeritus_member, date(2026, 5, 1), None)
    assert_authorship_periods(regular_member, [])
