import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod, Institute, Duty, DutyType, MemberDuty
from django.contrib.auth.models import User
import json

@pytest.mark.django_db
def test_add_member_with_temporary_duty_no_cf(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    print(user)
    institute = Institute.objects.create(name="Instituto Test")
    print(institute)
    
    duty_type = DutyType.objects.create(name="temporary")
    print(duty_type)
    duty = Duty.objects.create(name="Duty Test", duty_type=duty_type)
    print(duty)
    
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
                "start_date": timezone.now().date().isoformat(),
                "end_date": None,
            }
        ]),
    }
    
    response = client.post(url, data=payload)
    print(response)
    
    assert response.status_code == 200
    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")
    
    assert member is not None
    assert MemberDuty.objects.filter(member=member, duty=duty).exists()
    assert not AuthorshipPeriod.objects.filter(member=member).exists()
    assert not member.is_active_cf()
    assert not member.is_active_author()
    assert not member.future_authorship()