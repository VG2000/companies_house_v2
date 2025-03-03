import os
import pandas as pd
from django.core.management.base import BaseCommand
from company_data.models import LocalAdministrativeUnit, Postcode
from django.db import transaction

# Define BASE_DIR as the root of your project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class Command(BaseCommand):
    help = "Loads postcode data from a CSV file efficiently"

    def handle(self, *args, **kwargs):
        file_path = os.path.join(BASE_DIR, "postcode", "ONSPD_NOV_2024_UK.csv")

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {file_path}"))
            return

        # Check if models are already populated
        if Postcode.objects.exists():
            self.stdout.write("Postcode table is already populated. Skipping...")
            return
        
        self.stdout.write(self.style.SUCCESS(f"📂 Loading postcode data from {file_path}..."))

        chunksize = 50_000  # Process in batches to optimize memory

             # Define explicit dtypes for known columns (adjust as needed)
        dtype_spec = {
            "pcds": str,  # Ensure postcodes are read as strings
            "oslaua": str,  # Ensure Local Authority codes are read as strings
            "lat": "float64",  # Ensure numeric values are properly handled
            "long": "float64",
        }

        total_records = 0

        # Read CSV in chunks
        for chunk in pd.read_csv(file_path, chunksize=chunksize, dtype=dtype_spec, low_memory=False):
            bulk_insert_list = []
            
            for _, row in chunk.iterrows():
                district = LocalAdministrativeUnit.objects.filter(code=row["oslaua"]).first()
                if district:
                    bulk_insert_list.append(
                        Postcode(
                            code=row["pcds"],
                            district=district,
                            latitude=row.get("lat", None),
                            longitude=row.get("long", None),
                        )
                    )

            # Bulk insert in database
            if bulk_insert_list:
                with transaction.atomic():
                    Postcode.objects.bulk_create(bulk_insert_list, ignore_conflicts=True)
                total_records += len(bulk_insert_list)
                self.stdout.write(self.style.SUCCESS(f"✅ Processed {total_records} postcodes..."))

        self.stdout.write(self.style.SUCCESS("🎉 Postcode data successfully loaded!"))
