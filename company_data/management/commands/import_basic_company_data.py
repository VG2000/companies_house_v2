import csv
import os
import zipfile
import time
from datetime import datetime
import logging
from django.core.management.base import BaseCommand
from company_data.models import Company

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import company data from a zip file or a standalone CSV file"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help="Path to the zip file or CSV file")

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        # Log the start time
        start_time = time.time()

        # Check if the provided file is a zip file or CSV
        if zipfile.is_zipfile(file_path):
            self.process_zip(file_path)
        elif file_path.endswith('.csv'):
            self.stdout.write(f"Processing standalone CSV file: {file_path}")
            self.process_csv(file_path)
        else:
            self.stderr.write(self.style.ERROR("The provided file is neither a valid zip file nor a CSV file"))
            return

        # Log the end time and duration
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Processed {file_path} in {duration:.2f} seconds")
        self.stdout.write(self.style.SUCCESS(f"Processed {file_path} in {duration:.2f} seconds"))

    def process_zip(self, zip_path):
        extract_dir = 'extracted_csvs'

        self.stdout.write(f"Extracting zip file: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        self.stdout.write(self.style.SUCCESS(f"Extracted files to: {extract_dir}"))

        # Process each CSV file in the extracted folder
        for filename in os.listdir(extract_dir):
            if filename.endswith('.csv'):
                csv_path = os.path.join(extract_dir, filename)
                self.stdout.write(f"Processing file: {csv_path}")
                self.process_csv(csv_path)

        # Clean up extracted files
        self.cleanup_extracted_files(extract_dir)

    def process_csv(self, file_path):
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)

            # Normalize fieldnames to remove leading/trailing spaces
            reader.fieldnames = [field.strip() for field in reader.fieldnames]
        
            companies = []

            for row in reader:
                companies.append(
                    Company(
                        company_name=row.get('CompanyName'),
                        company_number=row.get('CompanyNumber'),
                        reg_address_care_of=row.get('RegAddress.CareOf'),
                        reg_address_po_box=row.get('RegAddress.POBox'),
                        reg_address_line1=row.get('RegAddress.AddressLine1'),
                        reg_address_line2=row.get('RegAddress.AddressLine2'),
                        reg_address_post_town=row.get('RegAddress.PostTown'),
                        reg_address_county=row.get('RegAddress.County'),
                        reg_address_country=row.get('RegAddress.Country'),
                        reg_address_postcode=row.get('RegAddress.PostCode'),
                        company_category=row.get('CompanyCategory'),
                        company_status=row.get('CompanyStatus'),
                        country_of_origin=row.get('CountryOfOrigin'),
                        dissolution_date=self.parse_date(row.get('DissolutionDate')),
                        incorporation_date=self.parse_date(row.get('IncorporationDate')),
                        accounts_account_ref_day=self.parse_int(row.get('Accounts.AccountRefDay')),
                        accounts_account_ref_month=self.parse_int(row.get('Accounts.AccountRefMonth')),
                        accounts_next_due_date=self.parse_date(row.get('Accounts.NextDueDate')),
                        accounts_last_made_up_date=self.parse_date(row.get('Accounts.LastMadeUpDate')),
                        accounts_account_category=row.get('Accounts.AccountCategory'),
                        returns_next_due_date=self.parse_date(row.get('Returns.NextDueDate')),
                        returns_last_made_up_date=self.parse_date(row.get('Returns.LastMadeUpDate')),
                        mortgages_num_mort_charges=self.parse_int(row.get('Mortgages.NumMortCharges')),
                        mortgages_num_mort_outstanding=self.parse_int(row.get('Mortgages.NumMortOutstanding')),
                        mortgages_num_mort_part_satisfied=self.parse_int(row.get('Mortgages.NumMortPartSatisfied')),
                        mortgages_num_mort_satisfied=self.parse_int(row.get('Mortgages.NumMortSatisfied')),
                        sic_code_1=row.get('SICCode.SicText_1'),
                        sic_code_2=row.get('SICCode.SicText_2'),
                        sic_code_3=row.get('SICCode.SicText_3'),
                        sic_code_4=row.get('SICCode.SicText_4'),
                        limited_partnerships_num_gen_partners=self.parse_int(row.get('LimitedPartnerships.NumGenPartners')),
                        limited_partnerships_num_lim_partners=self.parse_int(row.get('LimitedPartnerships.NumLimPartners')),
                        uri=row.get('URI'),
                        conf_stmt_next_due_date=self.parse_date(row.get('ConfStmtNextDueDate')),
                        conf_stmt_last_made_up_date=self.parse_date(row.get('ConfStmtLastMadeUpDate')),
                    )
                )
                if len(companies) >= 10000:
                    Company.objects.bulk_create(companies)
                    companies = []

            if companies:
                Company.objects.bulk_create(companies)

    def cleanup_extracted_files(self, extract_dir):
        for filename in os.listdir(extract_dir):
            os.remove(os.path.join(extract_dir, filename))
        os.rmdir(extract_dir)

    def parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date() if date_str else None
        except ValueError:
            return None

    def parse_int(self, int_str):
        try:
            return int(int_str) if int_str else None
        except ValueError:
            return None
