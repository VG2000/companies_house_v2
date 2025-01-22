import csv
import os
import zipfile
from datetime import datetime
from django.core.management.base import BaseCommand
from company_data.models import Company


class Command(BaseCommand):
    help = "Import company data from a zip file containing CSV files"

    def add_arguments(self, parser):
        parser.add_argument('zip_path', type=str, help="Path to the zip file containing CSV files")

    def handle(self, *args, **kwargs):
        zip_path = kwargs['zip_path']
        extract_dir = 'extracted_csvs'

        # Step 1: Extract the zip file
        if not zipfile.is_zipfile(zip_path):
            self.stderr.write(self.style.ERROR("The provided file is not a valid zip file"))
            return

        self.stdout.write(f"Extracting zip file: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        self.stdout.write(self.style.SUCCESS(f"Extracted files to: {extract_dir}"))

        # Step 2: Process each CSV file in the extracted folder
        for filename in os.listdir(extract_dir):
            if filename.endswith('.csv'):
                csv_path = os.path.join(extract_dir, filename)
                self.stdout.write(f"Processing file: {csv_path}")
                self.import_csv(csv_path)

        # Step 3: Clean up extracted files
        for filename in os.listdir(extract_dir):
            os.remove(os.path.join(extract_dir, filename))
        os.rmdir(extract_dir)

        self.stdout.write(self.style.SUCCESS('All data imported successfully!'))

    def import_csv(self, file_path):
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

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
                # Bulk insert in batches of 10,000 to optimize performance
                if len(companies) >= 10000:
                    Company.objects.bulk_create(companies)
                    companies = []

            # Insert remaining records
            if companies:
                Company.objects.bulk_create(companies)

    def parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        except ValueError:
            return None

    def parse_int(self, int_str):
        try:
            return int(int_str) if int_str else None
        except ValueError:
            return None
