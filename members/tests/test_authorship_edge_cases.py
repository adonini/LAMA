import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


def create_member(name="Edge", role="affiliated"):
    institute = Institute.objects.create(name=f"{name} Institute")
    member = Member.objects.create(
        name=name,
        surname="Case",
        primary_email=f"{name.lower()}-case@test.com",
        role=role,
    )
    return institute, member


def add_permanent_duty(member, start_date, end_date=None, name="Permanent Duty"):
    duty_type, _ = DutyType.objects.get_or_create(name="permanent")
    duty = Duty.objects.create(name=name, duty_type=duty_type)
    return MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=start_date,
        end_date=end_date,
    )


def add_temporary_duty(member, start_date, end_date=None, name="Temporary Duty"):
    duty_type, _ = DutyType.objects.get_or_create(name="temporary")
    duty = Duty.objects.create(name=name, duty_type=duty_type)
    return MemberDuty.objects.create(
        member=member,
        duty=duty,
        start_date=start_date,
        end_date=end_date,
    )


@pytest.mark.django_db
def test_cf_gap_after_first_authorship_restarts_without_second_initial_delay():
    institute, member = create_member("CfGap")
    MembershipPeriod.objects.create(member=member, institute=institute, start_date=d(2026, 1, 1))
    CommonFound.objects.create(member=member, start_date=d(2026, 1, 1), end_date=d(2026, 12, 31))
    CommonFound.objects.create(member=member, start_date=d(2027, 10, 1))
    add_permanent_duty(member, d(2026, 1, 1))

    recalculate_authorship_periods(member)

    assert_authorship_periods(
        member,
        [
            (d(2026, 7, 1), d(2027, 6, 30)),
            (d(2027, 10, 1), None),
        ],
    )


@pytest.mark.django_db
def test_membership_gap_with_continuous_cf_cuts_eligibility_and_restarts_without_second_delay():
    institute, member = create_member("MembershipGap")
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 1, 1),
        end_date=d(2026, 12, 31),
    )
    MembershipPeriod.objects.create(member=member, institute=institute, start_date=d(2027, 10, 1))
    CommonFound.objects.create(member=member, start_date=d(2026, 1, 1))
    add_permanent_duty(member, d(2026, 1, 1))

    recalculate_authorship_periods(member)

    assert_authorship_periods(
        member,
        [
            (d(2026, 7, 1), d(2027, 6, 30)),
            (d(2027, 10, 1), None),
        ],
    )


@pytest.mark.django_db
def test_cf_restarts_during_final_grace_merges_into_single_open_authorship():
    institute, member = create_member("CfGraceMerge")
    MembershipPeriod.objects.create(member=member, institute=institute, start_date=d(2026, 1, 1))
    CommonFound.objects.create(member=member, start_date=d(2026, 1, 1), end_date=d(2026, 12, 31))
    CommonFound.objects.create(member=member, start_date=d(2027, 3, 1))
    add_permanent_duty(member, d(2026, 1, 1))

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 7, 1), None)])


@pytest.mark.django_db
def test_candidate_start_equal_to_eligibility_end_still_creates_authorship_with_final_grace():
    institute, member = create_member("BoundaryIncluded")
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
        end_date=d(2026, 10, 9),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9), end_date=d(2026, 10, 9))
    add_temporary_duty(member, d(2026, 4, 12), end_date=d(2026, 7, 1))

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 10, 9), d(2027, 4, 9))])


@pytest.mark.django_db
def test_candidate_start_after_eligibility_end_creates_no_authorship():
    institute, member = create_member("BoundaryExcluded")
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
        end_date=d(2026, 10, 8),
    )
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9), end_date=d(2026, 10, 8))
    add_temporary_duty(member, d(2026, 4, 12), end_date=d(2026, 7, 1))

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [])


@pytest.mark.django_db
def test_temporary_support_windows_touching_by_one_day_are_continuous():
    institute, member = create_member("TouchingTemporary")
    MembershipPeriod.objects.create(member=member, institute=institute, start_date=d(2026, 3, 10))
    CommonFound.objects.create(member=member, start_date=d(2026, 4, 9))
    add_temporary_duty(member, d(2026, 4, 12), end_date=d(2026, 7, 1), name="Temporary Duty 2026")
    add_temporary_duty(member, d(2028, 2, 5), end_date=d(2028, 4, 1), name="Temporary Duty 2028")

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 10, 9), d(2029, 12, 31))])


@pytest.mark.django_db
def test_overlapping_cf_periods_do_not_create_duplicate_authorship_periods():
    institute, member = create_member("OverlappingCf")
    MembershipPeriod.objects.create(member=member, institute=institute, start_date=d(2026, 1, 1))
    CommonFound.objects.create(member=member, start_date=d(2026, 1, 1), end_date=d(2026, 12, 31))
    CommonFound.objects.create(member=member, start_date=d(2026, 6, 1))
    add_permanent_duty(member, d(2026, 1, 1))

    recalculate_authorship_periods(member)

    assert_authorship_periods(member, [(d(2026, 7, 1), None)])
