import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound
from django.contrib.auth.models import User
import json
from datetime import datetime

@pytest.mark.django_db
def test_add_member_with_permanent_duty_cf_early_above_6(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    
    duty_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)
    
    url = reverse('add-member')
    endUrl = reverse('end_duty')
    
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
                "end_date": None,
            }
        ]),
    }
    
    response = client.post(url, data=payload)
    
    assert response.status_code == 200
    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")

    print(payload)
    payload['id'] = str(member.id)
    payload['is_cf'] = 'on'
    payload['cf_start'] = datetime(2023, 10, 15).date().isoformat()
    del payload['new_duties']
    print(payload)
    response = client.post(url, data=payload)
    assert response.status_code == 200
    assert member is not None
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert CommonFound.objects.filter(member=member).exists()
    autorship = AuthorshipPeriod.objects.filter(member=member).first()
    print(autorship)
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 10, 15).date()

    end_payload = {
        "id": MemberDuty.objects.filter(member=member, duty=duty).first().id,
        "end-date": datetime(2025,2,5).date().isoformat()
    }
    response = client.post(endUrl, data=end_payload)
    assert response.status_code == 200
    autorship = AuthorshipPeriod.objects.filter(member=member).first()
    assert autorship.end_date == datetime(2025, 2, 5).date()
    assert not member.dated_authorship(datetime(2025, 2, 6).date())
    assert member.dated_authorship(datetime(2025, 2, 5).date())
