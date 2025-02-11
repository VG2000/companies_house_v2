import csv
from django.core.management.base import BaseCommand
from company_data.models import SicDivision, SicGroup, SicClass
import os

# Define BASE_DIR as the root of your project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class Command(BaseCommand):
    help = "Populates the SIC hierarchy tables from CSV files if they are empty."

    def handle(self, *args, **options):
        # Use the BASE_DIR to construct paths
        sic_data_path = os.path.join(BASE_DIR, "sic_data")

        # Use the updated paths in your code
        division_file = os.path.join(sic_data_path, "sic_division_codes.csv")
        group_file = os.path.join(sic_data_path, "sic_group_codes.csv")
        class_file = os.path.join(sic_data_path, "sic_class_codes.csv")

        # Check if models are already populated
        if SicDivision.objects.exists() or SicGroup.objects.exists() or SicClass.objects.exists():
            self.stdout.write("SIC tables are already populated. Skipping...")
            return

        # Load SicDivision data
        with open(division_file, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            divisions = []
            for row in reader:
                divisions.append(SicDivision(code=row["code"], description=row["description"]))
            SicDivision.objects.bulk_create(divisions)
            self.stdout.write(f"Loaded {len(divisions)} SIC Divisions.")

        # Load SicGroup data
        with open(group_file, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            groups = []
            for row in reader:
                division = SicDivision.objects.get(code=row["division_code"])
                groups.append(SicGroup(code=row["code"], division=division, description=row["description"]))
            SicGroup.objects.bulk_create(groups)
            self.stdout.write(f"Loaded {len(groups)} SIC Groups.")

        # Load SicClass data
        with open(class_file, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            classes = []
            for row in reader:
                division = SicDivision.objects.get(code=row["sic_division_code"])
                group = SicGroup.objects.get(code=row["sic_group_code"])
                classes.append(SicClass(code=row["code"], division=division, group=group, description=row["description"]))
            SicClass.objects.bulk_create(classes)
            self.stdout.write(f"Loaded {len(classes)} SIC Classes.")

        self.stdout.write(self.style.SUCCESS("SIC tables successfully populated."))
