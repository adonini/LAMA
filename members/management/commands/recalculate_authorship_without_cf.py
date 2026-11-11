from django.core.management.base import BaseCommand

from members.models import Member
from members.views import recalculate_authorship_periods


class Command(BaseCommand):
    help = 'Recalculate authorship for members assigned duties that do not require CF.'

    def handle(self, *args, **options):
        members = Member.objects.filter(
            duties__duty__grants_authorship_without_cf=True,
        ).distinct()

        for member in members.iterator():
            recalculate_authorship_periods(member)

        self.stdout.write(
            self.style.SUCCESS(
                f'Recalculated authorship for {members.count()} member(s).'
            )
        )
