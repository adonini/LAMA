from ..models import MembershipPeriod
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import OuterRef, Subquery, F
from django.core.mail import EmailMultiAlternatives


def send_digest(periods, starting_today):
    if not periods and not starting_today:
        return

    subject = "List of members starting/ending membership today"
    html_content = render_to_string(
        "emails/membership_ending_today.html",
        {
            "periods": periods,
            "count": len(periods),
            "starting_today": starting_today,
            "count_starting_today": len(starting_today),
        },
    )

    to_addr = "lst-telescope-manager@cta-observatory.org" #lst-telescope-manager@cta-observatory.org
    from_addr = "LAMA@cta-observatory.org"

    msg = EmailMultiAlternatives(
        subject=subject,
        body="This email requires an HTML-capable client.",
        from_email=from_addr,
        to=[to_addr],
        headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def run():
    today = timezone.localdate()

    latest_pk_sq = (
        MembershipPeriod.objects.filter(member_id=OuterRef("member_id"))
        .order_by("-end_date", "-start_date", "-pk")
        .values("pk")[:1]
    )

    periods = list(
        MembershipPeriod.objects.filter(end_date=today)
        .annotate(latest_pk=Subquery(latest_pk_sq))
        .filter(pk=F("latest_pk"))
        .select_related("member", "institute")
        .order_by("member__name", "member__surname")
    )

    starting_today = list(
        MembershipPeriod.objects.filter(start_date=today)
        .select_related("member", "institute")
        .order_by("member__name", "member__surname")
    )

    if periods or starting_today:
        send_digest(periods, starting_today)
