import pytest

from members.models import CommonFound, Duty, DutyType, Institute, Member, MemberDuty, MembershipPeriod
from members.tests.helpers import assert_authorship_periods, d
from members.views import recalculate_authorship_periods


@pytest.mark.django_db
def test_membership_end_before_temporary_eligibility_has_no_authorship():
    institute = Institute.objects.create(name="Institute Test")
    member = Member.objects.create(
        name="Member",
        surname="User",
        primary_email="membership-end@test.com",
        role="affiliated",
    )
    MembershipPeriod.objects.create(
        member=member,
        institute=institute,
        start_date=d(2026, 3, 10),
        end_date=d(2026, 8, 1),
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

    assert_authorship_periods(member, [])
