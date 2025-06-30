import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound
from django.contrib.auth.models import User
import json
from datetime import datetime

@pytest.mark.django_db
def test_add_member_with_temporary_duty_cf_early_under_6_enlarge_periods(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    
    duty_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)
    
    url = reverse('add-member')
    addUrl = reverse('add_duty')
    
    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": datetime(2022,3,10).date().isoformat(),
        "is_cf": 'off',
        "role": "affiliated",
        "new_duties": json.dumps([
            {
                "duty": duty.id,
                "start_date": datetime(2023,4,5).date().isoformat(),
                "end_date": datetime(2023,5,1).date().isoformat(),
            }
        ]),
    }
    
    response = client.post(url, data=payload)
    
    assert response.status_code == 200
    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")

    print(payload)
    payload['id'] = str(member.id)
    payload['is_cf'] = 'on'
    payload['cf_start'] = datetime(2023, 8, 15).date().isoformat()
    del payload['new_duties']
    print(payload)
    response = client.post(url, data=payload)
    assert response.status_code == 200
    assert member is not None
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert CommonFound.objects.filter(member=member).exists()
    autorship = AuthorshipPeriod.objects.filter(member=member).first()
    print(autorship.end_date)
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 10, 5).date()
    assert autorship.end_date == datetime(2024, 12, 31).date()
    print(AuthorshipPeriod.objects.filter(member=member))
    duty_payload = {
        'id': member.id,
        'duty': duty.id,
        'start_date': datetime(2024,8,15).date().isoformat(),
        'end_date': datetime(2024,9,10).date().isoformat(),
    }
    response = client.post(addUrl, data=duty_payload)
    assert response.status_code == 200
    autorship = AuthorshipPeriod.objects.filter(member=member).first()
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 10, 5).date()
    assert autorship.end_date == datetime(2025, 12, 31).date()
    print(AuthorshipPeriod.objects.filter(member=member))
    duty_payload = {
        'id': member.id,
        'duty': duty.id,
        'start_date': datetime(2026,5,1).date().isoformat(),
        'end_date': datetime(2026,6,2).date().isoformat(),
    }
    response = client.post(addUrl, data=duty_payload)
    assert response.status_code == 200
    autorship = AuthorshipPeriod.objects.filter(member=member).order_by("-start_date").first()
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2026, 1, 1).date()
    assert autorship.end_date == datetime(2027, 12, 31).date()
    print(AuthorshipPeriod.objects.filter(member=member))
    print(len(AuthorshipPeriod.objects.filter(member=member)))
    assert member.dated_authorship(datetime(2025, 12, 31).date()) != None
    assert member.dated_authorship(datetime(2026, 1, 1).date()) != None
