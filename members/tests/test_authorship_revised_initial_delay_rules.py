import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


def create_member_with_membership(role="affiliated", membership_start=None):
    institute = Institute.objects.create(name=f"Institute {role}")
    member = Member.objects.create(
        name="Member",
        surname=role,
        primary_email=f"{role}-initial-delay@test.com",
        role=role,
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=membership_start or d(2026, 3, 10),
    )
    return member


@pytest.mark.django_db
def test_non_student_existing_permanent_duty_starts_authorship_at_late_cf_start():
    member = create_member_with_membership()
    CommonFound.objects.create(member=member, start_date=d(2026, 11, 20))

    permanent_type = DutyType.objects.create(name="permanent")
    duty = Duty.objects.create(name="Permanent Duty", duty_type=permanent_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 11, 20), None)])


@pytest.mark.django_db
def test_non_student_existing_temporary_duty_starts_authorship_at_late_cf_start():
    member = create_member_with_membership()
    CommonFound.objects.create(member=member, start_date=d(2026, 11, 20))

    temporary_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Temporary Duty", duty_type=temporary_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
        end_date=d(2026, 7, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 11, 20), d(2027, 12, 31))])


@pytest.mark.django_db
def test_non_student_temporary_uses_cf_start_when_cf_is_after_year_start_before_duty():
    member = create_member_with_membership()
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

    assert_authorship_periods(member, [(d(2026, 10, 9), d(2027, 12, 31))])


@pytest.mark.django_db
def test_non_student_future_temporary_uses_year_start_when_cf_already_active():
    member = create_member_with_membership(membership_start=d(2025, 3, 10))
    CommonFound.objects.create(member=member, start_date=d(2025, 4, 9))

    temporary_type = DutyType.objects.create(name="temporary")
    duty = Duty.objects.create(name="Future Temporary Duty", duty_type=temporary_type)
    MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=d(2026, 4, 12),
        end_date=d(2026, 7, 1),
    )

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 7, 1), d(2027, 12, 31))])
