import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty, CommonFound
from django.contrib.auth.models import User
from dateutil.relativedelta import relativedelta
import json
from datetime import datetime

from members.tests.helpers import assert_single_authorship_period

@pytest.mark.django_db
def test_add_member_with_permanent_duty_cf_early_above_6_institute_chage_cf_unticked(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    institute2 = Institute.objects.create(name="I2", long_name="Instituto 2")
    
    duty_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)
    
    url = reverse('add-member')
    
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
    assert_single_authorship_period(member, datetime(2023, 10, 15).date(), None)

    payload['institute'] = str(institute2.id)
    payload['start_date'] = datetime(2025,3,10).date().isoformat()
    payload['is_cf'] = 'off'
    print(payload)
    response = client.post(url, data=payload)
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert response.status_code == 200
    end_date = (datetime(2025,3,10).date() + relativedelta(months=6) - relativedelta(days=1))
    assert_single_authorship_period(member, datetime(2023, 10, 15).date(), end_date)
    assert member.dated_authorship(end_date) is not None
    assert member.dated_authorship(end_date + relativedelta(days=1)) is None
    assert member.current_cf().end_date == datetime(2025,3,10).date()-relativedelta(days=1)
    assert member.membership_periods.order_by("-start_date").first().start_date == datetime(2025,3,10).date()
    assert MemberDuty.objects.filter(member=member, duty=duty, end_date__isnull=True).exists()
    assert CommonFound.objects.filter(member=member).exists()
    assert CommonFound.objects.filter(member=member).order_by("-start_date").first().end_date == datetime(2025,3,10).date()-relativedelta(days=1)
