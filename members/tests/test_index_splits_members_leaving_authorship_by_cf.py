from django.contrib.auth.models import User
from django.urls import reverse

import pytest

from members.models import AuthorshipPeriod, CommonFound, Member, MembershipPeriod


@pytest.mark.django_db
def test_index_splits_members_leaving_authorship_by_cf(client):
    user = User.objects.create_user(username="dashboard-user", password="testpass")
    client.force_login(user)

    cf_member = Member.objects.create(
        name="CF",
        surname="Member",
        primary_email="cf@example.com",
        role="researcher",
    )
    MembershipPeriod.objects.create(member=cf_member, start_date="2024-01-01")
    AuthorshipPeriod.objects.create(
        member=cf_member,
        start_date="2024-01-01",
        end_date="2024-10-01",
    )
    CommonFound.objects.create(member=cf_member, start_date="2024-01-01")

    non_cf_member = Member.objects.create(
        name="Non CF",
        surname="Member",
        primary_email="non-cf@example.com",
        role="researcher",
    )
    MembershipPeriod.objects.create(member=non_cf_member, start_date="2024-01-01")
    AuthorshipPeriod.objects.create(
        member=non_cf_member,
        start_date="2024-01-01",
        end_date="2024-09-01",
    )

    non_member_author = Member.objects.create(
        name="Former",
        surname="Member",
        primary_email="former@example.com",
        role="researcher",
    )
    MembershipPeriod.objects.create(
        member=non_member_author,
        start_date="2023-01-01",
        end_date="2024-05-15",
    )
    AuthorshipPeriod.objects.create(
        member=non_member_author,
        start_date="2024-01-01",
        end_date="2024-08-01",
    )

    future_author = Member.objects.create(
        name="Future",
        surname="Author",
        primary_email="future-author@example.com",
        role="researcher",
    )
    MembershipPeriod.objects.create(member=future_author, start_date="2024-01-01")
    AuthorshipPeriod.objects.create(
        member=future_author,
        start_date="2024-07-15",
        end_date="2024-10-15",
    )

    response = client.get(reverse("index"))

    assert response.status_code == 200
    assert response.context["cf_members_leaving_authorship"] == 1
    assert response.context["non_cf_members_leaving_authorship"] == 1
    assert response.context["non_members_with_authorship"] == 1

    content = response.content.decode()
    assert "CF Members Leaving Authorship within 6 Months" in content
    assert "Non-CF Members Leaving Authorship within 6 Months" in content
