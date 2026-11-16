from datetime import datetime, timezone

import pytest
from django.test import RequestFactory

from members import views
from members.models import (
    AuthorDetails,
    AuthorInstituteAffiliation,
    AuthorshipPeriod,
    Institute,
    Member,
)


EXPORTERS = [
    views.generate_aa_email,
    views.generate_aa,
    views.generate_apj,
    views.generate_arxiv,
    views.generate_mnras,
    views.generate_pos,
    views.generate_nature,
    views.generate_science,
]


@pytest.fixture
def author_with_reordered_affiliations():
    member = Member.objects.create(
        name="Irene",
        surname="Example",
        primary_email="irene.example@example.com",
        role="researcher",
    )
    AuthorshipPeriod.objects.create(
        member=member,
        start_date="2026-01-01",
        end_date="2026-12-31",
    )
    author = AuthorDetails.objects.create(
        member=member,
        author_name="I. Example",
        author_name_given="Irene",
        author_name_family="Example",
        author_email="irene.example@example.com",
    )
    first_institute = Institute.objects.create(
        name="First Institute",
        long_description="First active affiliation",
    )
    second_institute = Institute.objects.create(
        name="Second Institute",
        long_description="Second active affiliation",
    )
    shared_creation_date = datetime(2026, 6, 23, 23, 59, 59, tzinfo=timezone.utc)

    AuthorInstituteAffiliation.objects.create(
        author_details=author,
        institute=first_institute,
        order=1,
        creation_date=shared_creation_date,
        end_date=datetime(2026, 11, 9, 13, 12, 15, tzinfo=timezone.utc),
    )
    AuthorInstituteAffiliation.objects.create(
        author_details=author,
        institute=second_institute,
        order=1,
        creation_date=shared_creation_date,
    )
    AuthorInstituteAffiliation.objects.create(
        author_details=author,
        institute=first_institute,
        order=2,
        creation_date=shared_creation_date,
    )

    return author


@pytest.mark.django_db
@pytest.mark.parametrize("exporter", EXPORTERS, ids=lambda exporter: exporter.__name__)
def test_exporters_include_all_date_valid_affiliations(
    exporter,
    author_with_reordered_affiliations,
):
    request = RequestFactory().get("/export/", {"date": "2026-11-16"})

    response = exporter(request)
    content = response.content.decode()

    assert response.status_code == 200
    assert "I. Example" in content or "I.~Example" in content
    assert "First active affiliation" in content
    assert "Second active affiliation" in content


@pytest.mark.django_db
def test_valid_affiliations_exclude_closed_record_and_keep_requested_order(
    author_with_reordered_affiliations,
):
    affiliations = list(
        views.get_valid_author_affiliations(
            author_with_reordered_affiliations,
            datetime(2026, 11, 16).date(),
        )
    )

    assert [(affiliation.institute.name, affiliation.order) for affiliation in affiliations] == [
        ("Second Institute", 1),
        ("First Institute", 2),
    ]
