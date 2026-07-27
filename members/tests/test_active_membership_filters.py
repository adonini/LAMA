import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from members.models import (
    AuthorshipPeriod,
    Country,
    DutyType,
    Group,
    Institute,
    Member,
    MembershipPeriod,
)


@pytest.fixture
def active_member_with_future_end():
    country = Country.objects.create(name="Spain")
    group = Group.objects.create(name="IFAE", country=country)
    institute = Institute.objects.create(name="IFAE", group=group)

    member = Member.objects.create(
        name="Future",
        surname="End",
        primary_email="future.end@example.com",
        role="researcher",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date="2024-01-01",
        end_date="2024-11-01",
    )
    AuthorshipPeriod.objects.create(
        member=member,
        start_date="2024-01-01",
    )

    return member


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url_name", "id_key"),
    [
        ("api_member", "pk"),
        ("api_author", "pk"),
        ("get_member_duty", "id"),
    ],
)
def test_active_membership_with_future_end_survives_location_filters(
    client,
    active_member_with_future_end,
    url_name,
    id_key,
):
    DutyType.objects.get_or_create(name="permanent")
    DutyType.objects.get_or_create(name="temporary")
    user = User.objects.create_user(username="tester", password="password")
    client.force_login(user)

    response = client.get(
        reverse(url_name),
        {
            "draw": 1,
            "start": 0,
            "length": 10,
            "country": "Spain",
            "group": "IFAE",
            "institute": "IFAE",
            "showAll": "false",
        },
    )

    assert response.status_code == 200
    ids = {row[id_key] for row in response.json()["data"]}
    assert active_member_with_future_end.pk in ids
