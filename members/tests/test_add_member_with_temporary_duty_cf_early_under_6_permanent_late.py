import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound
from django.contrib.auth.models import User
import json
from datetime import datetime

@pytest.mark.django_db
def test_add_member_with_temporary_duty_cf_early_under_6_permanent_late(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    
    duty_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)
    duty_type2 = DutyType.objects.create(name="permanent")
    duty2 = Duty.objects.create(name="Permanent Duty Test", duty_type=duty_type2)
    
    url = reverse('add-member')
    addDuty = reverse('add_duty')
    
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
    autorship = AuthorshipPeriod.objects.filter(member=member).first()
    print(autorship.end_date)
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 10, 5).date()
    assert autorship.end_date == datetime(2024, 12, 31).date()
    assert len(AuthorshipPeriod.objects.filter(member=member)) == 1
    duty_payload = {
        "id": member.id,
        "duty": duty2.id,
        "start_date" : datetime(2024, 3, 11).date().isoformat(),
    }
    response = client.post(addDuty, data=duty_payload)
    assert response.status_code == 200
    assert member is not None
    assert len(AuthorshipPeriod.objects.filter(member=member)) == 1
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert MemberDuty.objects.filter(member=member, duty=duty2).exists()
    assert CommonFound.objects.filter(member=member).exists()
    autorship = AuthorshipPeriod.objects.filter(member=member).first()
    print(autorship.end_date)
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 10, 5).date()
    assert autorship.end_date == None
