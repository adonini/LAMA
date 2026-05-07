import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


@pytest.mark.django_db
def test_student_gap_between_temporary_duties_creates_two_periods():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Student",
        surname="Gap",
        primary_email="student-gap@test.com",
        role="student",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9))

    temporary_type = DutyType.objects.create(name="temporary")
    duty_1 = Duty.objects.create(name="Student Gap Duty 1", duty_type=temporary_type)
    duty_2 = Duty.objects.create(name="Student Gap Duty 2", duty_type=temporary_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty_1,
        start_date=d(2026, 4, 12),
        end_date=d(2026, 7, 1),
    )
    MemberDuty.objects.create(
        member=member,
        duty=duty_2,
        start_date=d(2029, 2, 5),
        end_date=d(2029, 4, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(
        member,
        [
            (d(2026, 9, 10), d(2027, 12, 31)),
            (d(2029, 1, 1), d(2030, 12, 31)),
        ],
    )
