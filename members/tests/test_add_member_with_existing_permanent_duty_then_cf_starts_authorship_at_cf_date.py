import json
from datetime import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty
from members.tests.helpers import assert_single_authorship_period


@pytest.mark.django_db
def test_add_member_with_existing_permanent_duty_then_cf_starts_authorship_at_cf_date(client):
    user = User.objects.create_user(username="testuser", password="testpass")
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")

    duty_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)

    url = reverse("add-member")

    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": datetime(2022, 3, 10).date().isoformat(),
        "is_cf": "off",
        "role": "affiliated",
        "new_duties": json.dumps(
            [
                {
                    "duty": duty.id,
                    "start_date": datetime(2023, 2, 5).date().isoformat(),
                    "end_date": None,
                }
            ]
        ),
    }

    response = client.post(url, data=payload)
    assert response.status_code == 200

    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert not CommonFound.objects.filter(member=member).exists()

    payload["id"] = member.id
    payload["is_cf"] = "on"
    payload["cf_start"] = datetime(2024, 2, 12).date().isoformat()
    del payload["new_duties"]

    response = client.post(url, data=payload)
    assert response.status_code == 200
    assert CommonFound.objects.filter(member=member).exists()
    assert_single_authorship_period(member, datetime(2024, 2, 12).date(), None)
