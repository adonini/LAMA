import pandas as pd
from django.core.management.base import BaseCommand
from members.models import Institute


class Command(BaseCommand):
    help = 'Updates or creates institutes based on the provided CSV file'

    def handle(self, *args, **options):
        file_path = '/code/inst.csv'
        try:
            # Read CSV file into DataFrame
            data = pd.read_csv(file_path)

            # Iterate over each row in the DataFrame
            for index, row in data.iterrows():
                # Extract data from the row
                name = row['Name'].strip()
                long_name = row['LongName'].strip()
                is_lst = str(row['isLST']).strip().lower() in ('y', 'yes', 'true', '1')  # Convert to boolean
                long_description = row['Long Description'].strip()

                # Check if the institute exists in the database
                institute, created = Institute.objects.get_or_create(
                    name=name,
                    defaults={
                        'long_name': long_name,
                        'is_lst': is_lst,
                        'long_description': long_description
                    }
                )

                # If the institute was created, print creation message; otherwise, update it
                if created:
                    self.stdout.write(f"Institute: {name} created in the database.")
                else:
                    self.stdout.write(f"Institute: {name} already exists. Updating details.")
                    # Update the institute if it already exists
                    institute.long_name = long_name
                    institute.is_lst = is_lst
                    institute.long_description = long_description
                    institute.save()

                self.stdout.write(f"  Long Name: {long_name}")
                self.stdout.write(f"  Is LST: {'Yes' if is_lst else 'No'}")
                self.stdout.write(f"  Long Description: {long_description}")
                self.stdout.write("-" * 40)

            self.stdout.write("Process complete. Institutes updated or created.")

        except FileNotFoundError:
            self.stderr.write(f"Error: The file '{file_path}' was not found.")
        except Exception as e:
            self.stderr.write(f"An error occurred: {e}")
