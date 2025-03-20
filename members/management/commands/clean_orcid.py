from django.core.management.base import BaseCommand
from members.models import AuthorDetails


class Command(BaseCommand):
    help = 'Clean NaN ORCID values from AuthorDetails and set them as empty'

    def handle(self, *args, **kwargs):
        # Fetch all AuthorDetails where ORCID is "NaN"
        author_details = AuthorDetails.objects.filter(orcid="NAN")

        updated_count = 0
        for author_detail in author_details:
            # Print the original ORCID value before updating
            self.stdout.write(f"Updating AuthorDetail {author_detail.id} with original ORCID: {author_detail.orcid}")

            # Set ORCID to an empty string
            author_detail.orcid = ""
            author_detail.save()

            updated_count += 1

            # Log the update
            self.stdout.write(f"AuthorDetail {author_detail.id} updated. New ORCID: {author_detail.orcid}")

        # Output the total number of updates
        self.stdout.write(f"{updated_count} AuthorDetails updated with empty ORCID values.")
