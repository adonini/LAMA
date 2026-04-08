from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import F, Max, OuterRef, Subquery
from django.template.loader import render_to_string
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from ..models import AuthorshipPeriod, MembershipPeriod, DigestReportState


REPORT_KEY = "membership_authorship_biweekly_digest"
TO_ADDR = [
    "apenuela@ifae.es",
    "lst-telescope-manager@cta-observatory.org",
]
FROM_ADDR = "LAMA@cta-observatory.org"


def get_or_create_state():
    state, _ = DigestReportState.objects.get_or_create(
        report_key=REPORT_KEY,
        defaults={
            "payload": {
                "authors_current_map": {}
            }
        },
    )
    return state


def get_reporting_window(state):
    today = timezone.localdate()

    if state.last_window_end:
        window_start = state.last_window_end
    else:
        window_start = today - relativedelta(days=14)

    window_end = today
    return window_start, window_end


def get_membership_started(window_start, window_end):
    return list(
        MembershipPeriod.objects.filter(
            start_date__gt=window_start,
            start_date__lte=window_end,
        )
        .select_related("member", "institute")
        .order_by("start_date", "member__surname", "member__name")
    )


def get_membership_ended(window_start, window_end):
    latest_pk_sq = (
        MembershipPeriod.objects.filter(member_id=OuterRef("member_id"))
        .order_by("-end_date", "-start_date", "-pk")
        .values("pk")[:1]
    )

    return list(
        MembershipPeriod.objects.filter(
            end_date__gt=window_start,
            end_date__lte=window_end,
        )
        .annotate(latest_pk=Subquery(latest_pk_sq))
        .filter(pk=F("latest_pk"))
        .select_related("member", "institute")
        .order_by("end_date", "member__surname", "member__name")
    )


def get_current_authorship_watchlist(reference_date):
    six_months = reference_date + relativedelta(months=6)

    last_end = (
        AuthorshipPeriod.objects
        .values("member_id")
        .annotate(last_end=Max("end_date"))
        .filter(last_end__gte=reference_date, last_end__lte=six_months)
    )

    latest_pk_sq = (
        AuthorshipPeriod.objects
        .filter(member_id=OuterRef("member_id"))
        .order_by("-end_date", "-pk")
        .values("pk")[:1]
    )

    periods_qs = (
        AuthorshipPeriod.objects
        .filter(member_id__in=last_end.values("member_id"))
        .annotate(latest_pk=Subquery(latest_pk_sq))
        .filter(pk=F("latest_pk"))
        .select_related("member")
        .order_by("end_date", "member__surname", "member__name")
    )

    periods = list(periods_qs)

    current_map = {
        str(period.member_id): {
            "end_date": str(period.end_date),
            "member_name": f"{period.member.name} {period.member.surname}".strip(),
        }
        for period in periods
    }

    return periods, current_map


def diff_authorship_watchlist(previous_map, current_periods, current_map):
    previous_ids = set(previous_map.keys())
    current_ids = set(current_map.keys())

    added_ids = current_ids - previous_ids
    removed_ids = previous_ids - current_ids
    common_ids = current_ids & previous_ids

    changed_ids = set()
    for member_id in common_ids:
        previous_end = previous_map.get(member_id, {}).get("end_date")
        current_end = current_map.get(member_id, {}).get("end_date")
        if previous_end != current_end:
            changed_ids.add(member_id)

    current_by_member_id = {str(period.member_id): period for period in current_periods}

    added_authors = [
        current_by_member_id[mid]
        for mid in sorted(added_ids, key=lambda x: current_map[x]["end_date"])
    ]

    changed_authors = [
        {
            "period": current_by_member_id[mid],
            "previous_end_date": previous_map[mid].get("end_date"),
            "current_end_date": current_map[mid].get("end_date"),
        }
        for mid in sorted(changed_ids, key=lambda x: current_map[x]["end_date"])
    ]

    removed_authors = []
    if removed_ids:
        removed_int_ids = [int(mid) for mid in removed_ids]

        latest_removed_pk_sq = (
            AuthorshipPeriod.objects
            .filter(member_id=OuterRef("member_id"))
            .order_by("-end_date", "-pk")
            .values("pk")[:1]
        )

        removed_periods = list(
            AuthorshipPeriod.objects
            .filter(member_id__in=removed_int_ids)
            .annotate(latest_pk=Subquery(latest_removed_pk_sq))
            .filter(pk=F("latest_pk"))
            .select_related("member")
            .order_by("member__surname", "member__name")
        )

        removed_by_member_id = {str(period.member_id): period for period in removed_periods}

        for mid in sorted(removed_ids):
            period = removed_by_member_id.get(mid)
            if period:
                removed_authors.append({
                    "period": period,
                    "previous_end_date": previous_map[mid].get("end_date"),
                })
            else:
                removed_authors.append({
                    "period": None,
                    "member_id": mid,
                    "member_name": previous_map[mid].get("member_name", f"Member {mid}"),
                    "previous_end_date": previous_map[mid].get("end_date"),
                })

    return added_authors, removed_authors, changed_authors


def build_context(
    window_start,
    window_end,
    membership_started,
    membership_ended,
    authors_added,
    authors_removed,
    authors_changed,
    authors_current,
):
    has_changes = any([
        len(membership_started) > 0,
        len(membership_ended) > 0,
        len(authors_added) > 0,
        len(authors_removed) > 0,
        len(authors_changed) > 0,
    ])

    return {
        "window_start": window_start,
        "window_end": window_end,
        "membership_started": membership_started,
        "membership_ended": membership_ended,
        "authors_added": authors_added,
        "authors_removed": authors_removed,
        "authors_changed": authors_changed,
        "authors_current": authors_current,
        "count_membership_started": len(membership_started),
        "count_membership_ended": len(membership_ended),
        "count_authors_added": len(authors_added),
        "count_authors_removed": len(authors_removed),
        "count_authors_changed": len(authors_changed),
        "count_authors_current": len(authors_current),
        "has_changes": has_changes,
    }


def send_digest(context):
    subject = (
        f"Summary of memberships and authorships "
        f"({context['window_start']} to {context['window_end']})"
    )

    html_content = render_to_string(
        "emails/biweekly_status_digest.html",
        context,
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body="This email requires an HTML-capable client.",
        from_email=FROM_ADDR,
        to=TO_ADDR,
        headers={
            "List-Unsubscribe": "<mailto:unsub@example.com>",
        },
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def save_state(state, window_end, current_map):
    state.last_run_at = timezone.now()
    state.last_window_end = window_end
    state.payload = {
        "authors_current_map": current_map,
    }
    state.save(update_fields=["last_run_at", "last_window_end", "payload", "updated_at"])


@transaction.atomic
def run():
    print("Running biweekly status digest...")

    state = get_or_create_state()
    window_start, window_end = get_reporting_window(state)

    print(f"Reporting window: ({window_start}, {window_end}]")

    membership_started = get_membership_started(window_start, window_end)
    membership_ended = get_membership_ended(window_start, window_end)

    authors_current, current_authors_map = get_current_authorship_watchlist(window_end)
    previous_authors_map = state.payload.get("authors_current_map", {})

    is_bootstrap = state.last_window_end is None

    if is_bootstrap:
        print("Initial bootstrap detected. Saving state without sending email.")
        save_state(state, window_end, current_authors_map)
        print("Bootstrap state saved.")
        print("Done.")
        return

    authors_added, authors_removed, authors_changed = diff_authorship_watchlist(
        previous_authors_map,
        authors_current,
        current_authors_map,
    )

    context = build_context(
        window_start=window_start,
        window_end=window_end,
        membership_started=membership_started,
        membership_ended=membership_ended,
        authors_added=authors_added,
        authors_removed=authors_removed,
        authors_changed=authors_changed,
        authors_current=authors_current,
    )

    print(f"Memberships started: {context['count_membership_started']}")
    print(f"Memberships ended: {context['count_membership_ended']}")
    print(f"Authors added to watchlist: {context['count_authors_added']}")
    print(f"Authors removed from watchlist: {context['count_authors_removed']}")
    print(f"Authors changed on watchlist: {context['count_authors_changed']}")
    print(f"Current authors watchlist: {context['count_authors_current']}")

    send_digest(context)
    if context["has_changes"]:
        print("Digest email sent with changes.")
    else:
        print("Digest email sent with no changes.")

    save_state(state, window_end, current_authors_map)
    print("State saved.")
    print("Done.")
