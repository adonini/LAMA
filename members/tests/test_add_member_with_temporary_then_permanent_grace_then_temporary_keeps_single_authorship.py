import json
from datetime import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty
from members.tests.helpers import assert_single_authorship_period


@pytest.mark.django_db
def test_add_member_with_temporary_then_permanent_then_temporary_keeps_single_authorship(client):
    user = User.objects.create_user(username="testuser", password="testpass")
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")

    temporary_type = DutyType.objects.create(name="temporary")
    permanent_type = DutyType.objects.create(name="permanent")
    temporary_1 = Duty.objects.create(name="Duty Temp 1", duty_type=temporary_type)
    permanent = Duty.objects.create(name="Duty Permanent", duty_type=permanent_type)
    temporary_2 = Duty.objects.create(name="Duty Temp 2", duty_type=temporary_type)

    add_member_url = reverse("add-member")
    add_duty_url = reverse("add_duty")
    end_duty_url = reverse("end_duty")

    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": datetime(2022, 3, 10).date().isoformat(),
        "is_cf": "on",
        "cf_start": datetime(2022, 4, 1).date().isoformat(),
        "role": "affiliated",
        "new_duties": json.dumps(
            [
                {
                    "duty": temporary_1.id,
                    "start_date": datetime(2022, 4, 9).date().isoformat(),
                    "end_date": datetime(2022, 6, 1).date().isoformat(),
                }
            ]
        ),
    }

    response = client.post(add_member_url, data=payload)
    assert response.status_code == 200

    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")
    assert CommonFound.objects.filter(member=member).exists()
    assert_single_authorship_period(
        member,
        datetime(2022, 10, 1).date(),
        datetime(2023, 12, 31).date(),
    )

    response = client.post(
        add_duty_url,
        data={
            "id": member.id,
            "duty": permanent.id,
            "start_date": datetime(2023, 3, 10).date(),
            "end_date": "",
        },
    )
    assert response.status_code == 200
    assert_single_authorship_period(member, datetime(2022, 10, 1).date(), None)

    permanent_assignment = MemberDuty.objects.get(member=member, duty=permanent)
    response = client.post(
        end_duty_url,
        data={
            "id": permanent_assignment.id,
            "end-date": datetime(2023, 11, 12).date(),
        },
    )
    assert response.status_code == 200
    assert_single_authorship_period(
        member,
        datetime(2022, 10, 1).date(),
        datetime(2023, 12, 31).date(),
    )

    response = client.post(
        add_duty_url,
        data={
            "id": member.id,
            "duty": temporary_2.id,
            "start_date": datetime(2024, 2, 5).date(),
            "end_date": datetime(2024, 3, 1).date(),
        },
    )
    assert response.status_code == 200
    assert_single_authorship_period(
        member,
        datetime(2022, 10, 1).date(),
        datetime(2025, 12, 31).date(),
    )
