from datetime import date

from members.models import AuthorshipPeriod


def d(year, month, day):
    return date(year, month, day)


def authorship_periods(member):
    return list(AuthorshipPeriod.objects.filter(member=member).order_by("start_date"))


def assert_authorship_periods(member, expected_periods):
    periods = [(period.start_date, period.end_date) for period in authorship_periods(member)]
    assert periods == expected_periods


def assert_single_authorship_period(member, start_date, end_date):
    assert_authorship_periods(member, [(start_date, end_date)])
