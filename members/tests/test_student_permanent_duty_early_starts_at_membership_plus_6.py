import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


@pytest.mark.django_db
def test_student_permanent_duty_early_starts_at_membership_plus_6():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Student",
        surname="Permanent",
        primary_email="student-permanent-early@test.com",
        role="student",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9))

    permanent_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Permanent Duty", duty_type=permanent_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 9, 10), None)])
