import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound
from django.contrib.auth.models import User
import json
from datetime import datetime

@pytest.mark.django_db
def test_add_member_with_temporary_duty_cf_early_above_6_institute_change_only(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    institute2 = Institute.objects.create(name="I2", long_name="Instituto 2")
    
    duty_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)
    
    url = reverse('add-member')
    
    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": datetime(2022,3,10).date().isoformat(),
        "is_cf": 'off',
        "role": "student",
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
    print(autorship.end_date)
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 1, 1).date()
    assert autorship.end_date == datetime(2024, 12, 31).date()


    payload['institute'] = str(institute2.id)
    payload['start_date'] = datetime(2025,3,10).date().isoformat()
    print(payload)
    response = client.post(url, data=payload)
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert CommonFound.objects.filter(member=member).exists()
    assert response.status_code == 200
    print(AuthorshipPeriod.objects.filter(member=member))
    autorship = AuthorshipPeriod.objects.filter(member=member).order_by("-start_date").first()
    print(autorship)
    print(autorship.end_date)
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 1, 1).date()
    assert autorship.end_date == datetime(2024, 12, 31).date()
    assert not member.is_active_author()
    assert member.is_active_cf()
    assert member.current_membership().start_date == datetime(2025,3,10).date()
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert not member.has_active_duty()
    assert not member.has_valid_duty()
    assert CommonFound.objects.filter(member=member).exists()
    assert member.current_cf().end_date == None

