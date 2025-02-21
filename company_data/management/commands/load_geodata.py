import os
import pandas as pd
from django.core.management.base import BaseCommand
from company_data.models import ITLLevel1, ITLLevel2, ITLLevel3, LocalAdministrativeUnit, LocalAuthorityDistrict
from django.db import transaction

# Define BASE_DIR dynamically
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class Command(BaseCommand):
    help = "Loads geographical data from a CSV file into the database"

    def handle(self, *args, **kwargs):
        file_path = os.path.join(BASE_DIR, "postcode", "LAD23_LAU121_ITL321_ITL221_ITL121_UK_LU.csv")

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {file_path}"))
            return

        self.stdout.write(self.style.SUCCESS(f"📂 Loading data from {file_path}..."))

        # Load CSV file with explicit dtypes
        dtype_spec = {
            "ITL121CD": str, "ITL121NM": str,
            "ITL221CD": str, "ITL221NM": str,
            "ITL321CD": str, "ITL321NM": str,
            "LAU121CD": str, "LAU121NM": str,
            "LAD23CD": str, "LAD23NM": str
        }
        
        df = pd.read_csv(file_path, dtype=dtype_spec)

        # Track inserted records
        total_records = 0
        bulk_itl1, bulk_itl2, bulk_itl3, bulk_lau, bulk_lad = [], [], [], [], []

        # Process each row efficiently
        for _, row in df.iterrows():
            # Create ITL Level 1
            itl1, created = ITLLevel1.objects.get_or_create(code=row["ITL121CD"], defaults={"name": row["ITL121NM"]})
            if created:
                bulk_itl1.append(itl1)

            # Create ITL Level 2
            itl2, created = ITLLevel2.objects.get_or_create(code=row["ITL221CD"], defaults={"name": row["ITL221NM"], "itl1": itl1})
            if created:
                bulk_itl2.append(itl2)

            # Create ITL Level 3
            itl3, created = ITLLevel3.objects.get_or_create(code=row["ITL321CD"], defaults={"name": row["ITL321NM"], "itl2": itl2})
            if created:
                bulk_itl3.append(itl3)

            # Create Local Administrative Unit (LAU)
            lau, created = LocalAdministrativeUnit.objects.get_or_create(code=row["LAU121CD"], defaults={"name": row["LAU121NM"], "lad": None})  # Temporary null LAD
            if created:
                bulk_lau.append(lau)

            # Create Local Authority District (LAD) & link to LAU
            lad, created = LocalAuthorityDistrict.objects.get_or_create(code=row["LAD23CD"], defaults={"name": row["LAD23NM"], "lau": lau})
            if created:
                bulk_lad.append(lad)

            # Link LAU to LAD
            lau.lad = lad
            lau.save(update_fields=["lad"])

            total_records += 1

            # Log progress every 10,000 rows
            if total_records % 10_000 == 0:
                self.stdout.write(self.style.SUCCESS(f"✅ Processed {total_records} rows..."))

        # Bulk insert new records
        with transaction.atomic():
            ITLLevel1.objects.bulk_create(bulk_itl1, ignore_conflicts=True)
            ITLLevel2.objects.bulk_create(bulk_itl2, ignore_conflicts=True)
            ITLLevel3.objects.bulk_create(bulk_itl3, ignore_conflicts=True)
            LocalAdministrativeUnit.objects.bulk_create(bulk_lau, ignore_conflicts=True)
            LocalAuthorityDistrict.objects.bulk_create(bulk_lad, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"🎉 Successfully loaded {total_records} records!"))

