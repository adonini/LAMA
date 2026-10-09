import csv
import io

import pytest
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from members.models import (
    AuthorshipPeriod,
    Country,
    Group,
    Institute,
    Member,
    MembershipPeriod,
)


CSV_HEADERS = [
    'Member ID',
    'First Name',
    'Last Name',
    'Email',
    'Role',
    'Institute',
    'Group',
    'Country',
    'Membership Start',
    'Membership End',
    'Authorship Start',
    'Authorship End',
]


def csv_rows(response):
    return list(csv.reader(io.StringIO(response.content.decode('utf-8'))))


@pytest.fixture
def authenticated_client(client):
    user = User.objects.create_user(username='dashboard-exporter', password='testpass')
    client.force_login(user)
    return client


@pytest.fixture
def affiliation():
    country = Country.objects.create(name='Spain')
    group = Group.objects.create(name='CSV Group', country=country)
    return Institute.objects.create(name='CSV Institute', group=group)


@pytest.mark.django_db
def test_members_becoming_authors_csv_matches_dashboard_count(authenticated_client, affiliation):
    today = timezone.now().date()
    member = Member.objects.create(
        name='Future',
        surname='Author',
        primary_email='future-author@test.com',
        role='researcher',
    )
    membership = MembershipPeriod.objects.create(
        member=member,
        institute=affiliation,
        start_date=today - relativedelta(years=1),
    )
    authorship = AuthorshipPeriod.objects.create(
        member=member,
        start_date=today + relativedelta(months=1),
        end_date=today + relativedelta(years=1),
    )

    dashboard = authenticated_client.get(reverse('index'))
    response = authenticated_client.get(reverse('export_members_becoming_authors'))
    rows = csv_rows(response)

    assert dashboard.context['members_becoming_authors'] == 1
    assert reverse('export_members_becoming_authors') in dashboard.content.decode()
    assert response.status_code == 200
    assert response['Content-Disposition'] == f'attachment; filename="members_becoming_authors_{today}.csv"'
    assert rows == [
        CSV_HEADERS,
        [
            str(member.id), 'Future', 'Author', 'future-author@test.com', 'Researcher',
            'CSV Institute', 'CSV Group', 'Spain', str(membership.start_date), '',
            str(authorship.start_date), str(authorship.end_date),
        ],
    ]


@pytest.mark.django_db
def test_non_members_leaving_authorship_csv_uses_latest_membership(authenticated_client, affiliation):
    today = timezone.now().date()
    member = Member.objects.create(
        name='Former',
        surname='Member',
        primary_email='former-member@test.com',
        role='engineer',
    )
    membership = MembershipPeriod.objects.create(
        member=member,
        institute=affiliation,
        start_date=today - relativedelta(years=2),
        end_date=today - relativedelta(days=1),
    )
    authorship = AuthorshipPeriod.objects.create(
        member=member,
        start_date=today - relativedelta(years=1),
        end_date=today + relativedelta(months=2),
    )

    dashboard = authenticated_client.get(reverse('index'))
    response = authenticated_client.get(reverse('export_non_members_leaving_authorship'))
    rows = csv_rows(response)

    assert dashboard.context['non_members_with_authorship'] == 1
    assert reverse('export_non_members_leaving_authorship') in dashboard.content.decode()
    assert response.status_code == 200
    assert response['Content-Disposition'] == f'attachment; filename="non_members_leaving_authorship_{today}.csv"'
    assert rows == [
        CSV_HEADERS,
        [
            str(member.id), 'Former', 'Member', 'former-member@test.com', 'Engineer',
            'CSV Institute', 'CSV Group', 'Spain', str(membership.start_date),
            str(membership.end_date), str(authorship.start_date), str(authorship.end_date),
        ],
    ]


@pytest.mark.django_db
def test_dashboard_hides_csv_buttons_when_counts_are_zero(authenticated_client):
    response = authenticated_client.get(reverse('index'))
    content = response.content.decode()

    assert response.context['members_becoming_authors'] == 0
    assert response.context['non_members_with_authorship'] == 0
    assert reverse('export_members_becoming_authors') not in content
    assert reverse('export_non_members_leaving_authorship') not in content


@pytest.mark.django_db
@pytest.mark.parametrize(
    'url_name',
    ['export_members_becoming_authors', 'export_non_members_leaving_authorship'],
)
def test_dashboard_csv_exports_require_login(client, url_name):
    response = client.get(reverse(url_name))

    assert response.status_code == 302
    assert reverse('login') in response.url
