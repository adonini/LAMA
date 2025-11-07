import pandas as pd
from django.core.management.base import BaseCommand
from members.models import Member, AuthorDetails, AuthorInstituteAffiliation, Institute


class Command(BaseCommand):
    help = "Populate AuthorDetails and AuthorInstituteAffiliation from a CSV file."

    def handle(self, *args, **kwargs):
        # Path to the CSV file
        file_path = '/code/LST_Authors_cleaned.csv'

        # Load the CSV file
        try:
            data = pd.read_csv(file_path, delimiter='\t', keep_default_na=False)
        except Exception as e:
            self.stderr.write(f"Error loading CSV file: {e}")
            return

        # Track missing members and institutes
        missing_members = []
        missing_institutes = []

        # Iterate over the rows and process data
        for index, row in data.iterrows():
            try:
                # Try to find the member using name and surname
                member = Member.objects.filter(
                    name=row['givenName'].strip(),
                    surname=row['familyName'].strip()
                ).first()

                if not member:
                    # Add to missing members list and skip to the next row
                    missing_members.append(f"{row['givenName']} {row['familyName']}")
                    continue

                # Create or update AuthorDetails
                author_details, created = AuthorDetails.objects.get_or_create(
                    member=member,
                    defaults={
                        'author_name': row['authorNamePaper'].strip(),
                        'author_name_given': row['authorNamePaperGiven'].strip(),
                        'author_name_family': row['authorNamePaperFamily'].strip(),
                        'author_email': row['Email'].strip(),
                        'orcid': row['orcid'].strip(),
                    }
                )
                if not created:
                    # Update existing AuthorDetails if needed
                    author_details.author_name = row['authorNamePaper'].strip()
                    author_details.author_name_given = row['authorNamePaperGiven'].strip()
                    author_details.author_name_family = row['authorNamePaperFamily'].strip()
                    author_details.author_email = row['Email'].strip()
                    author_details.orcid = row['orcid'].strip()
                    author_details.save()
                    self.stdout.write(f"Updated AuthorDetails for member: {member.name} {member.surname}")

                # Process institute affiliations
                for i in range(1, 4):  # Handle institutes 1 to 3
                    institute_name = row[f'institute_{i}'].strip()
                    if institute_name and institute_name != "NAN":
                        # Fetch the institute; log if not found
                        institute = Institute.objects.filter(name=institute_name).first()
                        if not institute:
                            missing_institutes.append(institute_name)
                            continue

                        # Create the affiliation if it doesn't exist
                        AuthorInstituteAffiliation.objects.get_or_create(
                            author_details=author_details,
                            institute=institute,
                            order=i
                        )
                        self.stdout.write(
                            f"Added institute '{institute.name}' to author '{member.name} {member.surname}' (Order: {i})"
                        )

            except Exception as e:
                self.stderr.write(f"Error processing row {index + 1}: {e}")

        # Log missing members
        if missing_members:
            self.stderr.write("\nMembers not found in the database:")
            for missing_member in missing_members:
                self.stderr.write(f"- {missing_member}")

        # Log missing institutes
        if missing_institutes:
            self.stderr.write("\nInstitutes not found in the database:")
            for missing_institute in set(missing_institutes):  # Use `set` to avoid duplicates
                self.stderr.write(f"- {missing_institute}")

        self.stdout.write("Population of AuthorDetails and AuthorInstituteAffiliation completed.")
