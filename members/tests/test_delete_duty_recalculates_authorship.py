from datetime import datetime

import pytest
from django.contrib.auth.models import Group as AuthGroup, User
from django.urls import reverse

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, assert_single_authorship_period
from members.views import recalculate_authorship_periods


DELETE_BUTTON_MARKUP = b'class="btn btn-sm btn-clear rounded-xl mt-0 deleteDutyBtn"'


def create_user_with_optional_admin(client, username, is_admin=False):
    user = User.objects.create_user(username=username, password="testpass")
    if is_admin:
        admin_group, _ = AuthGroup.objects.get_or_create(name="admin")
        user.groups.add(admin_group)
    client.force_login(user)
    return user


def create_member_with_membership(name, email, institute):
    member = Member.objects.create(
        name=name,
        surname="User",
        primary_email=email,
        role="affiliated",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=datetime(2022, 3, 10).date(),
    )
    return member


@pytest.mark.django_db
def test_delete_duty_button_is_only_visible_for_admins(client):
    institute = Institute.objects.create(name="Instituto Test")
    member = create_member_with_membership("Visible", "visible@test.com", institute)

    temporary_type = DutyType.objects.create(name="temporary")
    DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Duty Test", duty_type=temporary_type, maximum_members=2)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=datetime(2024, 5, 20).date(),
    )

    create_user_with_optional_admin(client, "admin-user", is_admin=True)
    manage_member_response = client.get(reverse("manage-member-pk", args=[member.id]))
    duty_record_response = client.get(reverse("duty-record", args=[duty.id]))

    assert manage_member_response.status_code == 200
    assert duty_record_response.status_code == 200
    assert DELETE_BUTTON_MARKUP in manage_member_response.content
    assert DELETE_BUTTON_MARKUP in duty_record_response.content

    create_user_with_optional_admin(client, "normal-user", is_admin=False)
    manage_member_response = client.get(reverse("manage-member-pk", args=[member.id]))
    duty_record_response = client.get(reverse("duty-record", args=[duty.id]))

    assert manage_member_response.status_code == 200
    assert duty_record_response.status_code == 200
    assert DELETE_BUTTON_MARKUP not in manage_member_response.content
    assert DELETE_BUTTON_MARKUP not in duty_record_response.content


@pytest.mark.django_db
def test_delete_valid_temporary_duty_recalculates_authorship(client):
    create_user_with_optional_admin(client, "admin-user", is_admin=True)
    institute = Institute.objects.create(name="Instituto Test")
    member = create_member_with_membership("Valid", "valid@test.com", institute)

    CommonFound.objects.create(member=member, start_date=datetime(2022, 4, 1).date())

    temporary_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Duty Test", duty_type=temporary_type)
    assignment = MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=datetime(2022, 4, 9).date(),
        end_date=datetime(2022, 6, 1).date(),
    )

    recalculate_authorship_periods(member)
    assert_single_authorship_period(
        member,
        datetime(2022, 10, 1).date(),
        datetime(2023, 12, 31).date(),
    )

    response = client.post(reverse("delete_duty"), data={"id": assignment.id})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["recalculated_authorship"] is True
    assert not MemberDuty.objects.filter(pk=assignment.id).exists()
    assert_authorship_periods(member, [])


@pytest.mark.django_db
def test_delete_old_temporary_duty_recalculates_and_rebuilds_authorship_from_remaining_support(client):
    create_user_with_optional_admin(client, "admin-user", is_admin=True)
    institute = Institute.objects.create(name="Instituto Test")
    member = create_member_with_membership("Invalid", "invalid@test.com", institute)

    CommonFound.objects.create(member=member, start_date=datetime(2022, 4, 1).date())

    temporary_type = DutyType.objects.create(name="temporary")
    permanent_type = DutyType.objects.create(name="permanent")
    old_temporary = Duty.objects.create(name="Old Temporary", duty_type=temporary_type)
    permanent = Duty.objects.create(name="Permanent Duty", duty_type=permanent_type)

    old_assignment = MemberDuty.objects.create(
        member=member,
        duty=old_temporary,
        start_date=datetime(2022, 4, 9).date(),
        end_date=datetime(2022, 6, 1).date(),
    )
    MemberDuty.objects.create(
        member=member,
        duty=permanent,
        start_date=datetime(2023, 3, 10).date(),
    )

    recalculate_authorship_periods(member)
    assert_single_authorship_period(member, datetime(2022, 10, 1).date(), None)

    response = client.post(reverse("delete_duty"), data={"id": old_assignment.id})

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["recalculated_authorship"] is True
    assert not MemberDuty.objects.filter(pk=old_assignment.id).exists()
    assert_single_authorship_period(member, datetime(2023, 9, 10).date(), None)
