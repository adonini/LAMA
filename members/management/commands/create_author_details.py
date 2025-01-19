from django.core.management.base import BaseCommand
from members.models import Member, AuthorDetails


class Command(BaseCommand):
    help = 'Checks authors who do not have an associated AuthorDetails and creates one with empty fields.'

    def handle(self, *args, **kwargs):
        # Fetch all members and filter in Python for active authors
        authors = Member.objects.all()

        for author in authors:
            if author.is_active_author():  # Check if the member has an active authorship
                # Check if the author has an associated AuthorDetails
                if not hasattr(author, 'author_details'):
                    # Create an empty AuthorDetails for the author
                    author_details, created = AuthorDetails.objects.get_or_create(
                        member=author,
                        author_name='',
                        author_name_given='',
                        author_name_family='',
                        author_email='',
                        orcid=''
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created AuthorDetails for {author.name} {author.surname}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'AuthorDetails already exists for {author.name} {author.surname}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'AuthorDetails already exists for {author.name} {author.surname}'))

        self.stdout.write(self.style.SUCCESS('Command completed successfully'))
