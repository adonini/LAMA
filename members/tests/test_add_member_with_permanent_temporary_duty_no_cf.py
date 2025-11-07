import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty
from django.contrib.auth.models import User
import json

@pytest.mark.django_db
def test_add_member_with_permanent_temporary_duty_no_cf(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    
    duty_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Duty Test Permanent", duty_type=duty_type)

    duty_type1 = DutyType.objects.create(name="temporary")
    duty1 = Duty.objects.create(name="Duty Test Temporary", duty_type=duty_type1)
    
    url = reverse('add-member')
    
    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": timezone.now().date().isoformat(),
        "is_cf": 'off',
        "role": "affiliated",
        "new_duties": json.dumps([
            {
                "duty": duty.id,
                "start_date": datetime(2025, 8, 15).date().isoformat(),
                "end_date": datetime(2025, 12, 17).date().isoformat(),
            },
            {
                "duty": duty1.id,
                "start_date": timezone.now().date().isoformat(),
                "end_date": None,
            },

        ]),
    }
    
    response = client.post(url, data=payload)
    
    assert response.status_code == 200
    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")
    
    assert member is not None
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert MemberDuty.objects.filter(member=member, duty=duty1).exists()
    assert not AuthorshipPeriod.objects.filter(member=member).exists()
