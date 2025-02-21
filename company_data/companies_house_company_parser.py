import pandas as pd
import os
import logging
import time
import requests
import base64


from company_data.models import Company
from django.conf import settings
from django.db import transaction
from company_data.constants import COMPANY_EXCEL_TO_MODEL_MAPPING
from company_data.utils import parse_date

# Create a named logger instead of using `logging.basicConfig()`
logger = logging.getLogger(__name__)

# API Configuration
API_KEY = "17c5f21f-c601-45af-825d-b7b8cafe95b2"
BASE_URL = "https://api.company-information.service.gov.uk"
AUTH_HEADER = f"Basic {base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')}"
HEADERS = {"Authorization": AUTH_HEADER}


# Filepath for the CSV data
CSV_FILE_PATH = os.path.join(settings.BASE_DIR, "data", "active_full_group_medium_companies.csv")

def process_company_data(file_path=CSV_FILE_PATH):
    """
    Reads company data from the CSV file, updates or creates records in the Company model,
    and calls update_full_accounts_paper_filed() only if new records are created.
    Logs periodic updates for large CSV files.
    """
    if not os.path.exists(file_path):
        logging.error(f"🚨 CSV file not found at: {file_path}")
        raise FileNotFoundError(f"CSV file not found at: {file_path}")
    
    logging.info(f"📥 Starting data import from {file_path}")

    # ✅ Define column data types to prevent dtype warnings
    dtype_spec = {col: str for col in COMPANY_EXCEL_TO_MODEL_MAPPING.keys()}  # Set all columns to strings

    # ✅ Read CSV and trim column headers
    df = pd.read_csv(file_path, dtype=dtype_spec, low_memory=False)
    df.columns = df.columns.str.strip()  # Trim leading & trailing spaces

    logging.info(f"📊 Total rows in CSV: {len(df)}")

    # ✅ Track counts
    new_records = 0
    updated_records = 0
    LOG_INTERVAL = 10_000  # Log every 10,000 rows

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

        # ✅ Create or update company record
        obj, created = Company.objects.update_or_create(
            company_number=company_data.get("company_number"),
            defaults=company_data
        )

        # ✅ Update counters
        if created:
            new_records += 1
        else:
            updated_records += 1

        # ✅ Log progress every 10,000 rows
        if (index + 1) % LOG_INTERVAL == 0:
            logging.info(f"📌 Processed {index + 1} rows - New: {new_records}, Updated: {updated_records}")

    # ✅ Final summary
    logging.info(f"✅ Data import completed! New records: {new_records}, Updated records: {updated_records}")



def fetch_and_update_company_data():
    """
    Function to update full accounts paper filed status and last statement URL.
    Runs normally inside the Django view.
    """
    logger.info("✅ Starting update_full_accounts_paper_filed...")
    companies = Company.objects.all()  # Fetch ID for bulk updates
    updated_companies = []
    sleep_time = 0.8  # API rate limit wait time

    for company in companies:
        url = f"{BASE_URL}/company/{company.company_number}/filing-history"

        logger.debug(f"🌍 Fetching filing history for company: {company.company_number}")
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Check if the company has a filing of type "AA"
            items = data.get("items", [])
            for item in items:
          
                if item.get("type") == "AA":
                    logger.info(f"📄 Processing document metadata for company: {company.company_number}")

                    paper_filed = item.get("paper_filed", False)
                    document_url = item.get("links", {}).get("document_metadata")

                    updated_companies.append(
                        Company(
                            id=company.id,
                            full_accounts_paper_filed=paper_filed,
                            last_full_statement_url=document_url if document_url else None,
                        )
                    )

                    logger.info(f"✅ Updated company {company.company_number}: full_accounts_paper_filed={paper_filed}")
                    break

        except requests.exceptions.RequestException as e:
       
            logger.error(f"❌ Error fetching data for company {company.company_number}: {e}")
            continue

        time.sleep(sleep_time)  # Sleep to comply with rate limit

    # Perform a bulk update to minimize DB queries
    if updated_companies:
        with transaction.atomic():
            Company.objects.bulk_update(updated_companies, ["full_accounts_paper_filed", "last_full_statement_url"])
        logger.info(f"🎉 Successfully updated {len(updated_companies)} companies.")
     


