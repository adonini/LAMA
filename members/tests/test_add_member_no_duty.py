import pytest
from django.urls import reverse
from django.utils import timezone
from members.models import Member, AuthorshipPeriod
from django.contrib.auth.models import User
from members.models import Institute

@pytest.mark.django_db
def test_add_member_no_duty(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.force_login(user)
    institute = Institute.objects.create(name="Instituto Test")
    url = reverse('add-member')
    print(url)
    payload = {
        "name": "Test",
        "surname": "User",
        "primary_email": "user@test.com",
        "institute": str(institute.id),
        "start_date": timezone.now().date().isoformat(),
        "is_cf": 'off',
        "role": "affiliated", 
    }

    response = client.post(url, data=payload)
    print(response)
    
    assert response.status_code == 200
    member = Member.objects.get(name="Test", surname="User", primary_email="user@test.com")

    assert member is not None
    assert not AuthorshipPeriod.objects.filter(member=member).exists()
    assert not member.is_active_cf()
    assert not member.is_active_author()
    assert not member.future_authorship()
