from ..models import ( AuthorshipPeriod, Member)
from django.template.loader import render_to_string
import os
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import Max, OuterRef, Subquery, F
from django.core.mail import EmailMultiAlternatives
import subprocess
import json, tempfile, time
from uuid import uuid4

LIST_PATH = "endingAuthorsList.txt"
def send_digest(added_members, removed_authors, lst):
    if not added_members and not removed_authors:
        return

    subject = "List of authors ending authorship in 6 months"
    html_content = render_to_string("emails/email.html", {
        "added_members": added_members,
        "removed_members": removed_authors,
        "list": lst,
        "count_added": len(added_members),
        "count_removed": len(removed_authors),
        "count_list": len(lst),
    })

    to_addr = "lst-telescope-manager@cta-observatory.org" #lst-telescope-manager@cta-observatory.org
    from_addr = "LAMA@cta-observatory.org"

    msg = EmailMultiAlternatives(
        subject=subject,
        body="This email requires an HTML-capable client.",
        from_email=from_addr,
        to=[to_addr],
        headers={
            "List-Unsubscribe": "<mailto:unsub@example.com>",
        },
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def run():
    print("Running Script...")
    if not os.path.exists(LIST_PATH):
        open(LIST_PATH, "w").close()

    with open(LIST_PATH, "r") as f:
        previous_ids = set()
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                previous_ids.add(int(s))
            except ValueError:
                continue

    now = timezone.now()
    six_months = now + relativedelta(months=6)

    last_end = (
        AuthorshipPeriod.objects
        .values("member_id")
        .annotate(last_end=Max("end_date"))
        .filter(last_end__gte=now, last_end__lte=six_months)
    )

    latest_pk_sq = (
        AuthorshipPeriod.objects
        .filter(member_id=OuterRef("member_id"))
        .order_by("-end_date")
        .values("pk")[:1]
    )

    periods_qs = (
        AuthorshipPeriod.objects
        .filter(member_id__in=last_end.values("member_id"))
        .annotate(latest_pk=Subquery(latest_pk_sq))
        .filter(pk=F("latest_pk"))
        .select_related("member")
        .order_by("end_date")
    )

    current_ids = set(periods_qs.values_list("member_id", flat=True))

    added_ids = sorted(current_ids - previous_ids)
    removed_ids = sorted(previous_ids - current_ids)

    with open(LIST_PATH, "w") as f:
        for mid in sorted(current_ids):
            f.write(f"{mid}\n")

    added_members = list(periods_qs.filter(member_id__in=added_ids))

    removed_members = list(
        AuthorshipPeriod.objects
        .annotate(latest_pk=Subquery(latest_pk_sq))
        .filter(pk=F("latest_pk"), member_id__in=removed_ids)
        .select_related("member")
        .order_by("end_date")
    )

    print("Date:")
    print(f"Added IDs: {added_ids}")
    print(f"Added Members: {added_members}")
    print(f"Count Added Members: {len(added_members)}")
    print(f"Removed IDs: {removed_ids}")
    print(f"Removed Members: {removed_members}")

    if added_ids or removed_ids:
        send_digest(added_members, removed_members, periods_qs)

    print("Done !")
