import os
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from company_data.models import ITLLevel1, ITLLevel2, ITLLevel3, LocalAdministrativeUnit

# Define BASE_DIR dynamically to construct paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class Command(BaseCommand):
    help = "Populates the ITL hierarchy tables from CSV files if they are empty."

    def handle(self, *args, **options):
        # Define file paths
        itl_data_path = os.path.join(BASE_DIR, "uk_geo_data")

        itl1_file = os.path.join(itl_data_path, "ITL1.csv")
        itl2_file = os.path.join(itl_data_path, "ITL2.csv")
        itl3_file = os.path.join(itl_data_path, "ITL3.csv")
        lau_file = os.path.join(itl_data_path, "LAU.csv")

        # Check if models are already populated
        if ITLLevel1.objects.exists() or ITLLevel2.objects.exists() or ITLLevel3.objects.exists() or LocalAdministrativeUnit.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ ITL tables are already populated. Skipping..."))
            return

        self.stdout.write(self.style.SUCCESS("📂 Loading ITL and LAU data..."))

        # Load ITL Level 1
        self.load_itl1(itl1_file)

        # Load ITL Level 2
        self.load_itl2(itl2_file)

        # Load ITL Level 3
        self.load_itl3(itl3_file)

        # Load Local Administrative Unit (LAU)
        self.load_lau(lau_file)

        self.stdout.write(self.style.SUCCESS("✅ ITL tables successfully populated."))

    def load_itl1(self, file_path):
        """Loads ITL Level 1 data."""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ ITL1 file not found: {file_path}"))
            return

        with open(file_path, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            itl1_records = [ITLLevel1(code=row["code"], name=row["name"]) for row in reader]

        with transaction.atomic():
            ITLLevel1.objects.bulk_create(itl1_records, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"✅ Loaded {len(itl1_records)} ITL1 records."))

    def load_itl2(self, file_path):
        """Loads ITL Level 2 data."""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ ITL2 file not found: {file_path}"))
            return

        with open(file_path, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            itl2_records = []
            for row in reader:
                itl1 = ITLLevel1.objects.filter(code=row["itl1"]).first()
                if itl1:
                    itl2_records.append(ITLLevel2(code=row["code"], name=row["name"], itl1=itl1))

        with transaction.atomic():
            ITLLevel2.objects.bulk_create(itl2_records, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"✅ Loaded {len(itl2_records)} ITL2 records."))

    def load_itl3(self, file_path):
        """Loads ITL Level 3 data."""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ ITL3 file not found: {file_path}"))
            return

        with open(file_path, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            itl3_records = []
            for row in reader:
                itl2 = ITLLevel2.objects.filter(code=row["itl2"]).first()
                if itl2:
                    itl3_records.append(ITLLevel3(code=row["code"], name=row["name"], itl2=itl2))

        with transaction.atomic():
            ITLLevel3.objects.bulk_create(itl3_records, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"✅ Loaded {len(itl3_records)} ITL3 records."))

    def load_lau(self, file_path):
        """Loads Local Administrative Unit (LAU) data."""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ LAU file not found: {file_path}"))
            return

        with open(file_path, newline='', encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            lau_records = []
            for row in reader:
                itl3 = ITLLevel3.objects.filter(code=row["itl3"]).first()
                lau_records.append(LocalAdministrativeUnit(code=row["code"], name=row["name"], itl3=itl3))

        with transaction.atomic():
            LocalAdministrativeUnit.objects.bulk_create(lau_records, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"✅ Loaded {len(lau_records)} LAU records."))
