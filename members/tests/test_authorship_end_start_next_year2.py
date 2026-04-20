import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound, AuthorDetails
from django.contrib.auth.models import User
import json
from datetime import datetime

from members.tests.helpers import assert_authorship_periods

@pytest.mark.django_db
def test_authorship_end_start_next_year2(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    
    duty_type1 = DutyType.objects.create(name="temporary")
    duty1 = Duty.objects.create(name="Temporary Duty Test", duty_type=duty_type1)
    
    duty2 = Duty.objects.create(name="Second Temporary Duty Test", duty_type=duty_type1)
    url = reverse('add-member')
    add_url = reverse('add_duty')
    
    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": datetime(2022,3,10).date().isoformat(),
        "is_cf": 'on',
        "cf_start": datetime(2023, 8, 15).date().isoformat(),
        "cf_end": '',
        "role": "affiliated",
        "new_duties": json.dumps([
            {
                "duty": duty1.id,
                "start_date": datetime(2024,11,5).date().isoformat(),
                "end_date": datetime(2025,1,1).date().isoformat(),
            },
        ]),
    }
    
    response = client.post(url, data=payload)
    
    assert response.status_code == 200
    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")

    del payload['new_duties']
    assert member is not None
    assert MemberDuty.objects.filter(member=member, duty=duty1).exists()
    assert CommonFound.objects.filter(member=member).exists()
    assert_authorship_periods(
        member,
        [(datetime(2024, 7, 1).date(), datetime(2025, 12, 31).date())],
    )
    authDetails = AuthorDetails.objects.filter(member=member)
    print(f'The author details for the user are: {authDetails}')
    client.post(add_url, data={
                    "id": member.id,
                    "duty": duty2.id,
                    "start_date": datetime(2026,4,15).date().isoformat(),
                    "end_date": datetime(2026,5,6).date().isoformat(),
                })
    print(AuthorshipPeriod.objects.filter(member=member).order_by('-start_date'))
    assert_authorship_periods(
        member,
        [(datetime(2024, 7, 1).date(), datetime(2027, 12, 31).date())],
    )
    assert member.dated_authorship(datetime(2026, 1, 1).date()) is not None
    assert member.dated_authorship(datetime(2026, 10, 14).date()) is not None
    assert member.dated_authorship(datetime(2027, 12, 31).date()) is not None
    assert member.dated_authorship(datetime(2028, 1, 1).date()) is None
