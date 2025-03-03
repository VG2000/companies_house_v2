import zipfile
import os
from pathlib import Path
from lxml import etree
import logging
import base64
import requests
import time
import re
from decimal import Decimal, InvalidOperation
from django.db import transaction, IntegrityError
from company_data.models import FinancialMetrics 

# Configure logging
logging.basicConfig(
    filename="zip_parser.log",  # Log file name
    level=logging.INFO,  # Log level (INFO, DEBUG, ERROR, etc.)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)


BASE_DIR = Path(__file__).resolve().parent
API_KEY = "17c5f21f-c601-45af-825d-b7b8cafe95b2"
BASE_URL = "https://api.company-information.service.gov.uk"
AUTH_HEADER = f"Basic {base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')}"
HEADERS = {"Authorization": AUTH_HEADER}

def extract_company_number(file_name):
    parts = file_name.split("_")  # Split by underscore
    if len(parts) > 2:  # Ensure there are enough parts
        return parts[2]  # Extract company number
    return None  # Return None if format is unexpected

def extract_filing_date(file_name):
    parts = file_name.split("_")  # Split by underscore
    if len(parts) > 3:  # Ensure there are enough parts
        date_str = parts[3].split(".")[0]  # Extract date and remove file extension
        if len(date_str) == 8 and date_str.isdigit():  # Ensure valid date format
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"  # Convert to YYYY-MM-DD format
    return None  # Return None if format is unexpected

def parse_zip_files(zip_folder="test_data"):
    """
    Loops through all ZIP files in a specified folder, processes their contents,
    and logs the number of items processed per file.
    """
    # Ensure the provided folder path is absolute
    zip_folder = os.path.abspath(zip_folder)

    # Check if the directory exists
    if not os.path.exists(zip_folder):
        logging.error(f"Error: The directory {zip_folder} does not exist.")
        return

    # Get all .zip files in the specified directory
    zip_files = [f for f in os.listdir(zip_folder) if f.endswith('.zip')]

    if not zip_files:
        logging.warning(f"No ZIP files found in {zip_folder}")
        return

    for zip_filename in zip_files[:1]:
        zip_path = os.path.join(zip_folder, zip_filename)

        logging.info(f"Processing ZIP file: {zip_filename}")

        try:
            # Open the ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all files in the ZIP archive
                file_list = zip_ref.namelist()
                items_processed = 0  # Counter for processed files

                for file_name in file_list:
                    company_number = extract_company_number(file_name)
                    parse_financial_metrics(zip_ref=zip_ref, file_name=file_name, company_number=company_number)
                    items_processed += 1  # Increment counter
                    print(items_processed)

            # Log the number of items processed for the ZIP file
            logging.info(f"Finished processing {zip_filename}. Total items processed: {items_processed}")

        except zipfile.BadZipFile:
            logging.error(f"Error: Unable to open {zip_filename}. Skipping.")
        except Exception as e:
            logging.error(f"Error processing {zip_filename}: {e}")

def check_company_details(company_number):
    """
    Fetches company details from Companies House API, extracts relevant information
    if the accounts type is 'full' or 'group', and formats it for database insertion.
    """

    sleep_time = 0.8  # Enforce API rate limit
    url = f"{BASE_URL}/company/{company_number}"
    
    logging.debug(f"Fetching company details for: {company_number}")
    time.sleep(sleep_time)  # Respect rate limit
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Raise HTTP errors
        company_data = response.json()  # Parse JSON response

        # Extract accounts type and check if it's 'full' or 'group'
        accounts_info = company_data.get("accounts", {})
        last_accounts = accounts_info.get("last_accounts", {})
        accounts_type = last_accounts.get("type", "").lower()

        if accounts_type in ["full", "group"]:
            # Extract relevant data
            company_name = company_data.get("company_name", "Unknown Company")
            registered_office = company_data.get("registered_office_address", {})
            sic_codes = company_data.get("sic_codes", [])

            # Format for database insertion
            company_details = {
                "company_number": company_number,
                "company_name": company_name,
                "address_line_1": registered_office.get("address_line_1", ""),
                "address_line_2": registered_office.get("address_line_2", ""),
                "locality": registered_office.get("locality", ""),
                "postal_code": registered_office.get("postal_code", ""),
                "country": registered_office.get("country", ""),
                "sic_codes": sic_codes,
            }

            logging.debug(f"✅ Extracted company details: {company_details}")
            print(company_details)
            return company_details  # Return formatted company details

        else:
            logging.debug(f"⚠️ Skipping company {company_number}: Accounts type '{accounts_type}' is not 'full' or 'group'.")
            return False

    except requests.exceptions.Timeout:
        logging.error("⏳ API request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ API request error: {e}")
        return None



# Define mapping for long field names
FIELD_NAME_MAPPING = {
    "IncreaseDecreaseInCashCashEquivalentsBeforeForeignExchangeDifferencesChangesInConsolidation": "IncreaseDecreaseInCashCashEquivalents"
}

def parse_financial_metrics(zip_ref, file_name, company_number):
    """
    Parses XML/XBRL/HTML files from a ZIP archive, extracts financial metrics,
    company details, and inserts or updates them in the FinancialMetrics Django model.
    """

    logging.debug(f"Processing {file_name} for company {company_number}...")

    # Fetch company details from Companies House API
    company_info = check_company_details(company_number)
    if not company_info:
        return  # Exit early if no company details found

    # Extract filing date from the filename
    filing_date = extract_filing_date(file_name)
    if not filing_date:
        logging.warning(f"⚠️ No valid filing date extracted from {file_name}. Skipping.")
        return

    # Extract company details
    company_name = company_info.get("company_name", None)
    address_line_1 = company_info.get("address_line_1", None)
    address_line_2 = company_info.get("address_line_2", None)
    locality = company_info.get("locality", None)
    postal_code = company_info.get("postal_code", None)
    country = company_info.get("country", None)

    # Extract SIC codes and map them to separate fields
    sic_codes = company_info.get("sic_codes", [])
    sic_code_1 = sic_codes[0] if len(sic_codes) > 0 else None
    sic_code_2 = sic_codes[1] if len(sic_codes) > 1 else None
    sic_code_3 = sic_codes[2] if len(sic_codes) > 2 else None
    sic_code_4 = sic_codes[3] if len(sic_codes) > 3 else None

    # Define financial metrics
    income_statement = ["TurnoverRevenue", "CostSales", "GrossProfitLoss", "ProfitLoss",
                        "AdministrativeExpenses", "OtherOperatingIncomeFormat1", "OperatingProfit",
                        "OperatingProfitLoss", "OtherInterestRecievablesSimilarIncomeFinanceIncome",
                        "ProfitLossOnOrdinaryActivitiesBeforeTax", "TaxTaxCreditOnProfitOrLossOnOrdinaryActivities",
                        "NetIncome", "GrossProfit"]

    balance_sheet = ["IntangibleAssets", "PropertyPlantEquipment", "InvestmentsFixedAssets",
                     "FixedAssets", "TotalInventories", "Debtors", "CashBankOnHand",
                     "CurrentAssets", "TotalAssetsLessCurrentLiabilities", "Creditors",
                     "TaxationIncludingDeferredTaxationBalanceSheetSubtotal", "NetCurrentAssetsLiabilities",
                     "NetAssetsLiabilities"]

    cash_flow_statement = ["NetCashFlowsFromUsedInOperatingActivities", "NetCashFlowsFromUsedInInvestingActivities",
                           "CashCashEquivalents", "IncreaseDecreaseInCashCashEquivalents"]

    # Combine all financial metrics
    financial_metrics = income_statement + balance_sheet + cash_flow_statement

    # Dictionary to store parsed values
    metric_values = {metric: None for metric in financial_metrics}

    # Process only relevant file types
    if file_name.endswith((".xml", ".xbrl", ".html", ".xhtml")):
        print(f"Fetching financial information for {company_number}")
        with zip_ref.open(file_name) as file:
            try:
                tree = etree.parse(file)
                root = tree.getroot()

                # Extract financial metric values
                for metric in financial_metrics:
                    metric_elements = root.xpath(f"//*[@name]", namespaces={})

                    for element in metric_elements:
                        name_attr = element.get("name", "")

                        # Extract portion after the colon (e.g., "c:GrossProfitLoss" → "GrossProfitLoss")
                        match = re.match(r".*:(\w+)$", name_attr)
                        if match:
                            metric_name = match.group(1)

                            # Map to correct model field name
                            model_field = FIELD_NAME_MAPPING.get(metric_name, metric_name)

                            if model_field == metric:
                                raw_value = element.text.strip() if element.text else "N/A"
                                sign = element.get("sign", "")

                                # Log the raw value before conversion
                                logging.debug(f"Processing metric '{metric}' with raw value: '{raw_value}'")

                                # Convert value to decimal (handling invalid cases)
                                try:
                                    clean_value = raw_value.replace(",", "").strip()
                                    if clean_value in ["-", "N/A", ""]:
                                        numeric_value = None  # Handle non-numeric cases
                                    else:
                                        numeric_value = Decimal(clean_value)
                                        if sign == "-":
                                            numeric_value = -numeric_value
                                except (InvalidOperation, ValueError) as e:
                                    logging.error(f"❌ Error converting value '{raw_value}' for metric '{metric}': {e}")
                                    numeric_value = None  # Fallback to None for invalid values

                                # Store the first occurrence
                                if metric_values[model_field] is None:
                                    metric_values[model_field] = numeric_value
                                    break  # Stop searching for this metric

            except etree.XMLSyntaxError as e:
                logging.error(f"⚠️ XML Parsing Error in {file_name}: {e}")
                return
            except Exception as e:
                logging.error(f"⚠️ Unexpected error while processing {file_name}: {e}")
                return

    logging.debug(f"Parsed metrics for {company_number} (Filing Date: {filing_date}): {metric_values}")

    # Insert or update financial data in Django model
    try:
        with transaction.atomic():
            obj, created = FinancialMetrics.objects.update_or_create(
                company_number=company_number,
                filing_date=filing_date,
                defaults={
                    **metric_values,  # Financial metrics
                    "company_name": company_name,
                    "address_line_1": address_line_1,
                    "address_line_2": address_line_2,
                    "locality": locality,
                    "postal_code": postal_code,
                    "country": country,
                    "sic_code_1": sic_code_1,
                    "sic_code_2": sic_code_2,
                    "sic_code_3": sic_code_3,
                    "sic_code_4": sic_code_4
                }
            )
        logging.debug(f"✅ Data {'created' if created else 'updated'} for Company {company_number} on {filing_date}")

    except IntegrityError as e:
        logging.error(f"❌ Database IntegrityError while inserting/updating {company_number} on {filing_date}: {e}")
    except Exception as e:
        logging.error(f"❌ Unexpected database error while inserting/updating {company_number}: {e}")



if __name__ == '__main__':
       check_company_details("02235387")