from django.core.management.base import BaseCommand
from django.db import transaction
from members.models import Member, Country, Group, Institute, Duty
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import members from a CSV file into the database'

    def handle(self, *args, **kwargs):
        file_path = '/code/LST_members.csv'
        data = pd.read_csv(file_path)

        failed_rows = []
        new_members_count = 0

        with transaction.atomic():
            for _, row in data.iterrows():
                try:
                    # Create or get Country
                    country, _ = Country.objects.get_or_create(name=str(row['Country']).strip())

                    # Create or get Group, linking it to the Country
                    group, _ = Group.objects.get_or_create(name=str(row['Group']).strip(), country=country)

                    # Create or get Institute, linking it to the Group
                    institute, _ = Institute.objects.get_or_create(name=str(row['Institute']).strip(), group=group)

                    # Handle multiple duties, splitting them by commas
                    duties = [duty.strip() for duty in row['Duty'].split(',')] if pd.notna(row['Duty']) else []

                    # Parse dates with error handling
                    def parse_date(date_str):
                        try:
                            return datetime.strptime(date_str, '%b %d, %Y').date() if pd.notna(date_str) else None
                        except ValueError:
                            return None

                    member_start = parse_date(row['Member Start'])
                    member_end = parse_date(row['Member End'])
                    author_start = parse_date(row['Author Start'])
                    author_end = parse_date(row['Author End'])

                    # Create or update the Member
                    member, created = Member.objects.update_or_create(
                        primary_email=str(row['Email']).strip() if pd.notna(row['Email']) else '',
                        defaults={
                            'name': str(row['First Name']).strip(),
                            'surname': str(row['Last Name']).strip(),
                            'start_date': member_start,
                            'end_date': member_end,
                            'is_author': str(row['Author']).strip().lower() == 'yes',
                            'authorship_start': author_start,
                            'authorship_end': author_end,
                            'institute': institute,
                            'role': str(row['Role']).strip().lower(),
                        }
                    )

                    if created:
                        new_members_count += 1  # Increment count if a new member was created

                    # Assign each duty to the member
                    for duty_name in duties:
                        duty, _ = Duty.objects.get_or_create(name=duty_name)
                        member.duties.get_or_create(duty=duty, start_date=member_start)

                    self.stdout.write(self.style.SUCCESS(f"Processed {member}"))

                except Exception as e:
                    # Log the error to both the logger and stdout
                    error_message = f"Failed to process {row['First Name']} {row['Last Name']}: {e}"
                    logger.error(error_message)
                    self.stdout.write(self.style.ERROR(error_message))  # Immediate output to console
                    failed_rows.append({'first_name': row['First Name'], 'last_name': row['Last Name'], 'error': str(e)})

        # Summary of any failed rows after the import
        if failed_rows:
            self.stdout.write(self.style.WARNING("Some rows failed to process:"))
            for failed_row in failed_rows:
                self.stdout.write(self.style.WARNING(f"{failed_row['first_name']} {failed_row['last_name']}: {failed_row['error']}"))
        else:
            self.stdout.write(self.style.SUCCESS("All rows processed successfully."))

        # Output the total number of new members added
        self.stdout.write(self.style.SUCCESS(f'Total new members added: {new_members_count}'))

        self.stdout.write(self.style.SUCCESS('Data import completed.'))
