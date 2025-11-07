import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound
from django.contrib.auth.models import User
from dateutil.relativedelta import relativedelta
import json
from datetime import datetime

@pytest.mark.django_db
def test_add_member_with_permanent_duty_and_temporary_cf_early_above_6_institute_chage_cf_unticked_duty_ended_order_2(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    institute2 = Institute.objects.create(name="I2", long_name="Instituto 2")
    
    duty_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Duty Test Long", duty_type=duty_type)

    duty_type1 = DutyType.objects.create(name="temporary")
    duty1 = Duty.objects.create(name="Duty Test Short", duty_type=duty_type1)
    
    url = reverse('add-member')
    endUrl = reverse('end_duty')
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
    end_date = (datetime(2025,4,11).date() + relativedelta(months=6) - relativedelta(days=1))
    duty_payload={
        'id': member.id,
        'duty': duty1.id,
        'start_date': datetime(2025,3,10).date(),
        'end_date': datetime(2025,4,10).date()
    }
    response = client.post(addUrl, data=duty_payload)
    assert response.status_code == 200
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    print(MemberDuty.objects.filter(member=member).first().end_date)
    assert member.has_valid_duty()
    remove_duty = {
        'id': MemberDuty.objects.filter(member=member, duty=duty).first().id,
        'end-date': datetime(2025,3,25).date()
    }
    response = client.post(endUrl, data=remove_duty)
    assert MemberDuty.objects.filter(member=member, duty=duty, end_date__isnull=False).exists()
    assert not member.has_active_duty()
    assert member.has_valid_duty()

    payload['institute'] = str(institute2.id)
    payload['start_date'] = datetime(2025,4,11).date().isoformat()
    payload['is_cf'] = 'off'
    print(payload)
    response = client.post(url, data=payload)
    assert CommonFound.objects.filter(member=member).order_by("-start_date").first().end_date == datetime(2025,4,10).date()
    assert response.status_code == 200
    autorship = AuthorshipPeriod.objects.filter(member=member).order_by("-start_date").first()
    assert AuthorshipPeriod.objects.filter(member=member).exists()
    assert autorship.start_date == datetime(2023, 10, 15).date()
    assert autorship.end_date == end_date
    assert member.is_active_author()
    assert not member.is_active_cf()
    assert member.current_membership().start_date == datetime(2025,4,11).date()
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert CommonFound.objects.filter(member=member).exists()
    assert CommonFound.objects.filter(member=member).first().end_date == datetime(2025,4,11).date()-relativedelta(days=1)
