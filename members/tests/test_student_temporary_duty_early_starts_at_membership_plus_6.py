import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


@pytest.mark.django_db
def test_student_temporary_duty_early_starts_at_membership_plus_6():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Student",
        surname="Temporary",
        primary_email="student-temporary-early@test.com",
        role="student",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9))

    temporary_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Temporary Duty", duty_type=temporary_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
        end_date=d(2026, 7, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 9, 10), d(2027, 12, 31))])


@pytest.mark.django_db
def test_student_temporary_duty_uses_year_start_when_student_is_already_eligible():
    institute = Institute.objects.create(name="Institute Eligible Student")
    member = Member.objects.create(
        name="Student",
        surname="Temporary Future",
        primary_email="student-temporary-future@test.com",
        role="student",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2024, 11, 1),
    )
    CommonFound.objects.create(member=member, start_date=d(2024, 11, 1))

    temporary_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Temporary Duty", duty_type=temporary_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 7, 6),
        end_date=d(2026, 7, 26),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 1, 1), d(2027, 12, 31))])
