from ..models import ( AuthorshipPeriod, Member)
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import os
from dateutil.relativedelta import relativedelta
from django.utils import timezone

LIST_PATH = "endingAuthorsList.txt"
TO_ADDRESS = "jpenuela@ujaen.es" #lst-telescope-manager@cta-observatory.org 

def send_digest(added_members, removed_authors, list):
    """Send email with text+HTML if there are changes."""
    if not added_members and not removed_authors:
        return

    context = {
        "added_members": added_members,
        "removed_members": removed_authors,
        "list": list,
        "count_added": len(added_members),
        "count_removed": len(removed_authors),
        "count_list": len(list),
    }

    text_content = render_to_string("emails/email.txt", context)
    html_content = render_to_string("emails/email.html", context)

    msg = EmailMultiAlternatives(
        subject="List of authors ending authorship in 6 months",
        body=text_content,
        from_email=None,                 # uses DEFAULT_FROM_EMAIL from settings
        to=[TO_ADDRESS],
        headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=False)

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
        current_qs = (
            AuthorshipPeriod.objects
            .select_related("member")
            .filter(end_date__gte=now, end_date__lte=six_months).order_by("end_date")
        )
        current_ids = set(a.member_id for a in current_qs)

        added_ids = sorted(current_ids - previous_ids)
        removed_ids = sorted(previous_ids - current_ids)

        with open(LIST_PATH, "w") as f:
            for mid in sorted(current_ids):
                f.write(f"{mid}\n")

        added_members = list(current_qs.filter(member_id__in=added_ids))
        removed_members = list(AuthorshipPeriod.objects.filter(member__in=Member.objects.filter(pk__in=removed_ids)))

        print(f"Date:")
        print(f"Added IDs: {added_ids}")
        print(f"Added Members: {added_members}")
        print(f"Count Added Members: {len(added_members)}")
        print(f"Removed IDs: {removed_ids}")
        print(f"Removed Members: {removed_members}")

        if added_ids or removed_ids:
            send_digest(added_members, removed_members, current_qs)

    print("Done !")