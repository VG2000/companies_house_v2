import os
import logging
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from company_data.models import Company
from company_data.constants import COMPANY_EXCEL_TO_MODEL_MAPPING
from company_data.utils import parse_date

# ✅ Configure Logger
logger = logging.getLogger(__name__)

# Define BASE_DIR as the root of your project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ✅ CSV File Path
CSV_FILE_PATH = os.path.join(BASE_DIR, "data", "active_full_group_medium_companies.csv")

def process_company_data(file_path=CSV_FILE_PATH):
    """Processes the CSV file and updates/creates company records in the database."""
    if not os.path.exists(file_path):
        logger.error(f"🚨 CSV file not found: {file_path}")
        return

    logger.info(f"📥 Starting company data import from {file_path}")

    # ✅ Define column data types for consistency
    dtype_spec = {col: str for col in COMPANY_EXCEL_TO_MODEL_MAPPING.keys()}

    # ✅ Read CSV with safe parsing
    df = pd.read_csv(file_path, dtype=dtype_spec, low_memory=False)
    df.columns = df.columns.str.strip()  # Trim column names

    logger.info(f"📊 Total rows in CSV: {len(df)}")

    # ✅ Bulk insert/update tracking
    new_records = 0
    updated_records = 0
    LOG_INTERVAL = 10_000  # Log every 10,000 rows

    bulk_updates = []
    bulk_creates = []

    for index, row in df.iterrows():
        company_data = {
            model_field: row[excel_field]
            for excel_field, model_field in COMPANY_EXCEL_TO_MODEL_MAPPING.items()
            if excel_field in df.columns and pd.notna(row[excel_field])
        }

        # ✅ Convert date fields safely
        date_fields = [
            "dissolution_date", "incorporation_date", "accounts_next_due_date",
            "accounts_last_made_up_date", "returns_next_due_date", "returns_last_made_up_date",
            "conf_stmt_next_due_date", "conf_stmt_last_made_up_date"
        ]
        for field in date_fields:
            if field in company_data:
                company_data[field] = parse_date(company_data[field])

        # ✅ Prepare for bulk create/update
        company_number = company_data.get("company_number")
        existing_company = Company.objects.filter(company_number=company_number).first()

        if existing_company:
            for key, value in company_data.items():
                setattr(existing_company, key, value)
            bulk_updates.append(existing_company)
            updated_records += 1
        else:
            bulk_creates.append(Company(**company_data))
            new_records += 1

        # ✅ Log progress every 10,000 rows
        if (index + 1) % LOG_INTERVAL == 0:
            logger.info(f"📌 Processed {index + 1} rows - New: {new_records}, Updated: {updated_records}")

    # ✅ Bulk save changes
    with transaction.atomic():
        if bulk_creates:
            Company.objects.bulk_create(bulk_creates, ignore_conflicts=True)
        if bulk_updates:
            Company.objects.bulk_update(bulk_updates, list(COMPANY_EXCEL_TO_MODEL_MAPPING.values()))

    logger.info(f"✅ Data import completed! New: {new_records}, Updated: {updated_records}")


class Command(BaseCommand):
    """Django management command to import company data from a CSV file."""

    help = "Loads company data from CSV into the database."

    def handle(self, *args, **kwargs):
        """Command execution logic."""
        logger.info("🚀 Running load_company_data command...")
        process_company_data()
        logger.info("✅ load_company_data command completed successfully.")
