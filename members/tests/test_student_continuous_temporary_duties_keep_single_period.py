import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


@pytest.mark.django_db
def test_student_continuous_temporary_duties_keep_single_period():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Student",
        surname="Continuous",
        primary_email="student-continuous@test.com",
        role="student",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9))

    temporary_type = DutyType.objects.create(name="temporary")
    duty_1 = Duty.objects.create(name="Student Temporary Duty 1", duty_type=temporary_type)
    duty_2 = Duty.objects.create(name="Student Temporary Duty 2", duty_type=temporary_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty_1,
        start_date=d(2026, 4, 12),
        end_date=d(2026, 7, 1),
    )
    MemberDuty.objects.create(
        member=member,
        duty=duty_2,
        start_date=d(2027, 3, 5),
        end_date=d(2027, 5, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 9, 10), d(2028, 12, 31))])
