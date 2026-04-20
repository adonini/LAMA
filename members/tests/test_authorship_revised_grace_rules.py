import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


@pytest.mark.django_db
def test_final_grace_after_membership_end_does_not_require_active_cf_membership_or_duty():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Researcher",
        surname="Grace",
        primary_email="researcher-final-grace@test.com",
        role="affiliated",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
        end_date=d(2027, 8, 1),
    )
    CommonFound.objects.create(
        member=member,
        start_date=d(2026, 4, 9),
        end_date=d(2027, 8, 1),
    )

    permanent_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Permanent Duty", duty_type=permanent_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
        end_date=d(2027, 8, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 10, 12), d(2028, 2, 1))])


@pytest.mark.django_db
def test_permanent_duty_end_before_initial_delay_finishes_creates_no_authorship():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Researcher",
        surname="ShortDuty",
        primary_email="researcher-short-duty@test.com",
        role="affiliated",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9))

    permanent_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Short Permanent Duty", duty_type=permanent_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
        end_date=d(2026, 7, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [])
