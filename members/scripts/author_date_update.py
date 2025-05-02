from ..models import ( AuthorshipPeriod, AuthorDetails,
                     AuthorInstituteAffiliation)
from datetime import timedelta, datetime
from pytz import UTC
from django.utils.timezone import make_aware

def run():
    authorAffiliations = AuthorInstituteAffiliation.objects.all()

    print("Updating affiliation times")

    for affiliation in authorAffiliations:
        period = AuthorshipPeriod.objects.filter(member=affiliation.author_details.member).order_by('start_date').first()
        if period.start_date != affiliation.creation_date:
            try:
                affiliation.creation_date = make_aware(datetime(period.start_date.year, period.start_date.month, period.start_date.day), timezone=UTC)
                affiliation.save()
            except Exception as e:
                affiliation.creation_date = make_aware(datetime(period.start_date.year, period.start_date.month, period.start_date.day), timezone=UTC)+timedelta(hours=1)
                affiliation.save()

    print("Finished !")