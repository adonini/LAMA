from ..models import ( AuthorshipPeriod, AuthorDetails,
                     AuthorInstituteAffiliation, DutyType)
from datetime import timedelta, datetime
from pytz import UTC
from django.utils.timezone import make_aware
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import os
from datetime import datetime
from django.db.models import Q
from dateutil.relativedelta import relativedelta

def send_mal(list):
    # First, render the plain text content.
    text_content = render_to_string(
        "templates/emails/my_email.txt",
        context={"new_authors": list},
    )

    # Secondly, render the HTML content.
    html_content = render_to_string(
        "templates/emails/my_email.html",
        context={"new_authors": list},
    )

    # Then, create a multipart email instance.
    msg = EmailMultiAlternatives(
        "Subject here",
        text_content,
        "from@example.com",
        ["to@example.com"],
        headers={"List-Unsubscribe": "<mailto:unsub@example.com>"},
    )

    # Lastly, attach the HTML content to the email instance and send.
    msg.attach_alternative(html_content, "text/html")
    msg.send()

def run():
    with open("endingAuthorsList.txt", "r+") as f:
        names = set(line.strip().lower() for line in f)
        original_names = names.copy()
        removed_users = []
        added_users = []
        today = datetime.now()
        six_months_future = today + relativedelta(months=6)
        currentEndingAuthors = AuthorshipPeriod.objects.filter(
            end_date__gte=today, end_date__lte=six_months_future
        )
        print(len(currentEndingAuthors))
        print(len(names))
        f.seek(0)
        f.truncate(0)
        for author in currentEndingAuthors:
            name_str = author.member.name+" "+author.member.surname
            if name_str not in names:
                f.write(name_str+"\n")
                added_users.append(name_str)
            else:
                f.write(name_str+"\n")
        if len(names) != len(currentEndingAuthors):
            for name in names:
                name_parts = name.split(" ")
                if not currentEndingAuthors.filter(member__name=name_parts[0], member__surname=name_parts[1]).exists():
                    removed_users.append(name)
        print(len(removed_users))

            