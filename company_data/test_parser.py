import os
import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from pathlib import Path
from lxml import etree
from django.db import transaction
from django.conf import settings
from lxml import etree
import itertools
import csv
import base64
import time
import json
import requests
import tempfile
from company_data.models import Company, FinancialMetrics, FinancialStatement

# API Configuration
API_KEY = "17c5f21f-c601-45af-825d-b7b8cafe95b2"
BASE_URL = "https://api.company-information.service.gov.uk"
AUTH_HEADER = f"Basic {base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')}"
HEADERS = {"Authorization": AUTH_HEADER}

# Define CSV File Path
CSV_FILE_PATH = "updated_companies.csv"

# Configure logging
logger = logging.getLogger("test_logger")

STATEMENTS_DIR = Path("statements/")

INCOME_STATEMENT = [
    "TurnoverRevenue", "CostSales", "GrossProfitLoss", "ProfitLoss",
    "AdministrativeExpenses", "OtherOperatingIncomeFormat1", "OperatingProfit",
    "OperatingProfitLoss", "OtherInterestRecievablesSimilarIncomeFinanceIncome",
    "ProfitLossOnOrdinaryActivitiesBeforeTax", "TaxTaxCreditOnProfitOrLossOnOrdinaryActivities",
    "NetIncome", "GrossProfit"
]

BALANCE_SHEET = [
    "IntangibleAssets", "PropertyPlantEquipment", "InvestmentsFixedAssets",
    "FixedAssets", "TotalInventories", "Debtors", "CashBankOnHand",
    "CurrentAssets", "TotalAssetsLessCurrentLiabilities", "Creditors",
    "TaxationIncludingDeferredTaxationBalanceSheetSubtotal", "NetCurrentAssetsLiabilities",
    "NetAssetsLiabilities"
]

CASH_FLOW_STATEMENT = [
    "NetCashFlowsFromUsedInOperatingActivities", "NetCashFlowsFromUsedInInvestingActivities",
    "CashCashEquivalents", "IncreaseDecreaseInCashCashEquivalents"
]

FINANCIAL_METRICS = INCOME_STATEMENT + BALANCE_SHEET + CASH_FLOW_STATEMENT

FIELD_NAME_MAPPING = {
    "IncreaseDecreaseInCashCashEquivalentsBeforeForeignExchangeDifferencesChangesInConsolidation": "IncreaseDecreaseInCashCashEquivalents"
}

# def extract_company_number(file_name):
#     parts = file_name.split("_")
#     company_number = parts[2] if len(parts) > 2 else None
#     test_logger.debug(f"Extracted company number: {company_number} from filename: {file_name}")
#     return company_number

# def extract_filing_date(file_name):
#     parts = file_name.split("_")
#     if len(parts) > 3:
#         date_str = parts[3].split(".")[0]
#         if len(date_str) == 8 and date_str.isdigit():
#             filing_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
#             test_logger.debug(f"Extracted filing date: {filing_date} from filename: {file_name}")
#             return filing_date
#     return None


# def parse_financial_metrics(file_path):
#     file_name = file_path.name
#     test_logger.info(f"Starting to parse file: {file_name}")

#     company_number = extract_company_number(file_name)
#     filing_date = extract_filing_date(file_name)

#     if not company_number or not filing_date:
#         test_logger.warning(f"Skipping {file_name}: Invalid company number or filing date.")
#         return

#     test_logger.info(f"Processing {file_name} for company {company_number} (Filing Date: {filing_date})")

#     metric_values = {metric: None for metric in FINANCIAL_METRICS}

#     if file_name.endswith((".xml", ".xbrl", ".html", ".xhtml")):
#         try:
#             with file_path.open("rb") as file:
#                 tree = etree.parse(file)
#                 root = tree.getroot()
#                 namespaces = root.nsmap if root.nsmap else {}

#                 for metric in FINANCIAL_METRICS:
#                     try:
#                         metric_elements = root.xpath(f"//ix:nonFraction[@name]", namespaces=namespaces)
#                         for element in metric_elements:
#                             name_attr = element.get("name", "")
#                             match = re.match(r".*:(\w+)$", name_attr)
#                             if match:
#                                 metric_name = match.group(1)
#                                 model_field = FIELD_NAME_MAPPING.get(metric_name, metric_name)
#                                 if model_field == metric:
#                                     raw_value = element.text.strip() if element.text else "N/A"
#                                     sign = element.get("sign", "")
#                                     numeric_value = clean_number(raw_value)
#                                     if sign == "-" and numeric_value is not None:
#                                         numeric_value = -numeric_value
#                                     if metric_values[model_field] is None:
#                                         metric_values[model_field] = numeric_value
#                                         test_logger.debug(f"Extracted {model_field}: {numeric_value} from {file_name}")
#                                         break
#                     except Exception as e:
#                         test_logger.error(f"Error extracting metric '{metric}' in {file_name}: {e}")
#         except etree.XMLSyntaxError as e:
#             test_logger.error(f"XML Parsing Error in {file_name}: {e}")
#             return
#         except Exception as e:
#             test_logger.error(f"Unexpected error processing {file_name}: {e}")
#             return
    
#     test_logger.info(f"Extracted financial data for {company_number} (Filing Date: {filing_date}): {metric_values}")
#     save_financial_metrics(company_number, filing_date, metric_values)

# @transaction.atomic
# def save_financial_metrics(company_number, filing_date, metric_values):
#     try:
#         test_logger.debug(f"Attempting to save data for {company_number} on {filing_date}: {metric_values}")
        
#         financial_data, created = FinancialMetrics.objects.update_or_create(
#             company_number=company_number,
#             filing_date=filing_date,
#             defaults=metric_values
#         )
#         if created:
#             test_logger.info(f"Inserted new financial data for {company_number} on {filing_date}")
#         else:
#             test_logger.info(f"Updated financial data for {company_number} on {filing_date}")
#     except Exception as e:
#         test_logger.error(f"Database error saving data for {company_number}: {e}")

def test_process_statements():
    if not STATEMENTS_DIR.exists():
        logger.error(f"Statements directory '{STATEMENTS_DIR}' does not exist.")
        return
    
    # Get a list of actual files
    files = [file for file in STATEMENTS_DIR.iterdir() if file.is_file()]
    logger.info(f"Total files found in '{STATEMENTS_DIR}': {len(files)}")

    # Process only the first 3 files
    for file_path in itertools.islice(files, 3):
        logger.info(f"Processing: {file_path}")
        parse_financial_metrics(file_path)



def test_fetch_and_update_company_data():
    """
    Fetch company filing history, update database, and log results to CSV.
    """
    logger.info("✅ Starting fetch_and_update_company_data...")
    
    companies = Company.objects.all()
    sleep_time = 0.8  # API rate limit wait time

    # Open the CSV file in append mode (ensures previous data is kept)
    with open(CSV_FILE_PATH, mode="w", newline="") as file:
        writer = csv.writer(file)
        
        # Write CSV header
        writer.writerow(["Company Number", "Paper Filed", "Last Statement URL"])

        updated_companies = []

        for index, company in enumerate(companies, start=1):
            url = f"{BASE_URL}/company/{company.company_number}/filing-history"
            logger.debug(f"🌍 Fetching filing history for {company.company_number} (Company {index}/{len(companies)})")

            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Check for "AA" filing type
                items = data.get("items", [])
                for item in items:
                    if item.get("type") == "AA":
                        paper_filed = item.get("paper_filed", False)
                        document_url = item.get("links", {}).get("document_metadata", "")

                        # Store updates in bulk update list
                        updated_companies.append(
                            Company(
                                id=company.id,
                                full_accounts_paper_filed=paper_filed,
                                last_full_statement_url=document_url if document_url else None,
                            )
                        )

                        # Write data to CSV immediately
                        writer.writerow([company.company_number, paper_filed, document_url])
                        file.flush()  # Ensure data is written to disk

                        logger.info(f"✅ Updated {company.company_number}: paper_filed={paper_filed}")
                        break  # Stop processing further filings

            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Error fetching data for {company.company_number}: {e}")
                continue

            # Sleep to comply with API rate limit
            time.sleep(sleep_time)

            # Every 500 updates, commit to the database (prevent excessive memory usage)
            if len(updated_companies) >= 500:
                with transaction.atomic():
                    Company.objects.bulk_update(updated_companies, ["full_accounts_paper_filed", "last_full_statement_url"])
                logger.info(f"🎉 Batch commit: {len(updated_companies)} companies updated.")
                updated_companies.clear()  # Clear memory

        # Final bulk update after loop completion
        if updated_companies:
            with transaction.atomic():
                Company.objects.bulk_update(updated_companies, ["full_accounts_paper_filed", "last_full_statement_url"])
            logger.info(f"🎉 Final commit: {len(updated_companies)} companies updated.")

    logger.info("🏁 Finished processing all companies.")



def test_fetch_first_unfiled_statement():
    """
    Fetches the first last_full_statement_url where full_accounts_paper_filed is False,
    and makes a request to the Companies House API.
    """
    # Get the first company that meets the criteria
    company = Company.objects.filter(full_accounts_paper_filed=False, last_full_statement_url__isnull=False).first()

    if not company:
        logger.warning("⚠️ No companies found with full_accounts_paper_filed=False and a valid last_full_statement_url.")
        return None

    url = company.last_full_statement_url
    logger.info(f"🌍 Fetching statement from URL: {url} for company {company.company_number}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Raise error for HTTP failures (e.g., 404, 500)

        logger.info(f"✅ Successfully fetched statement for {company.company_number}")
        return response.json()  # Return the parsed JSON response

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error fetching data from {url} for company {company.company_number}: {e}")
        return None
    



# def parse_financial_metrics(file_path, company_number):
#     """
#     Parses an XHTML file and extracts financial metrics, handling XML namespaces correctly.
#     """
#     file_name = os.path.basename(file_path)
#     logger.info(f"🛠️ Parsing XHTML file: {file_name} for company {company_number}")

#     try:
#         with open(file_path, "rb") as file:
#             tree = etree.parse(file)
#             root = tree.getroot()

#             # Print the available namespaces in the document
#             namespaces = root.nsmap
#             logger.debug(f"🗂️ Detected XML Namespaces: {namespaces}")

#             # Identify the correct namespace prefix for Inline XBRL (ix)
#             ix_prefix = None
#             for prefix, uri in namespaces.items():
#                 if uri and "inlineXBRL" in uri.lower():
#                     ix_prefix = prefix
#                     break

#             if not ix_prefix:
#                 logger.error("❌ Could not detect Inline XBRL namespace (ix). Parsing will fail.")
#                 return
            
#             logger.info(f"🔎 Using Inline XBRL namespace prefix: {ix_prefix}")

#             # Extract financial data
#             metric_values = {}
#             for metric in FINANCIAL_METRICS:
#                 try:
#                     metric_elements = root.xpath(f"//{ix_prefix}:nonFraction[@name]", namespaces=namespaces)
                    
#                     for element in metric_elements:
#                         name_attr = element.get("name", "")
#                         if name_attr.endswith(f":{metric}"):
#                             raw_value = element.text.strip() if element.text else "N/A"
#                             sign = element.get("sign", "")
#                             numeric_value = clean_number(raw_value)

#                             if sign == "-" and numeric_value is not None:
#                                 numeric_value = -numeric_value

#                             metric_values[metric] = numeric_value
#                             logger.debug(f"📊 Extracted {metric}: {numeric_value}")
#                             break
#                 except Exception as e:
#                     logger.error(f"⚠️ Error extracting metric '{metric}' in {file_name}: {e}")

#             logger.info(f"✅ Extracted financial data for {company_number}: {metric_values}")

#             # Save to database
#             save_financial_metrics(company_number, metric_values)

#     except etree.XMLSyntaxError as e:
#         logger.error(f"❌ XML Parsing Error in {file_name}: {e}")
#     except Exception as e:
#         logger.error(f"❌ Unexpected error processing {file_name}: {e}")



# def clean_number(value):
#     """
#     Converts string to Decimal if possible.
#     """
#     if isinstance(value, str) and value.strip() in ["", "-", "N/A"]:
#         return None
#     try:
#         return Decimal(value.replace(",", "").strip())
#     except (InvalidOperation, ValueError):
#         logger.error(f"❌ Error converting value '{value}' to Decimal")
#         return None


# @transaction.atomic
# def save_financial_metrics(company_number, metric_values):
#     """
#     Saves extracted financial data to the FinancialMetrics model.
#     """
#     try:
#         financial_data, created = FinancialMetrics.objects.update_or_create(
#             company_number=company_number,
#             defaults=metric_values
#         )
#         if created:
#             logger.info(f"✅ Inserted new financial data for {company_number}")
#         else:
#             logger.info(f"🔄 Updated financial data for {company_number}")
#     except Exception as e:
#         logger.error(f"❌ Database error saving data for {company_number}: {e}")


######## NEW CODE ##########

        # Known XBRL standards for both `core` and `bus`
XBRL_STANDARDS = {
    "core": [
        "http://xbrl.frc.org.uk/fr/2023-01-01/core",
        "http://xbrl.frc.org.uk/fr/2022-01-01/core",
        "http://xbrl.frc.org.uk/fr/2021-01-01/core",
    ],
    "bus": [
        "http://xbrl.frc.org.uk/cd/2023-01-01/business",
        "http://xbrl.frc.org.uk/cd/2022-01-01/business",
        "http://xbrl.frc.org.uk/cd/2021-01-01/business",
    ],
}

def fetch_and_parse_all_statements():
    """
    Fetches and parses `application/xhtml+xml` financial statements 
    for all companies where `full_accounts_paper_filed=False` and 
    `last_full_statement_url` is available.
    """
    logger.info("🚀 Starting fetch_and_parse_all_statements...")

    # Get all eligible companies
    companies = Company.objects.filter(full_accounts_paper_filed=False, last_full_statement_url__isnull=False)
    sleep_time = 0.8  # Rate limit wait time
    processed_count = 0

    if not companies.exists():
        logger.warning("⚠️ No companies found with full_accounts_paper_filed=False and a valid last_full_statement_url.")
        return

    for company in companies:
        url = company.last_full_statement_url
        logger.info(f"🌍 Fetching statement metadata from URL: {url} for company {company.company_number}")

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            json_data = response.json()
            resources = json_data.get("resources", {})

            # Extract the XHTML URL if available
            xhtml_resource = resources.get("application/xhtml+xml", {})
            if not xhtml_resource:
                logger.error(f"❌ No XHTML document available for company {company.company_number}. Skipping...")
                continue

            xhtml_url = json_data["links"]["document"]
            logger.info(f"📄 Fetching XHTML document from: {xhtml_url}")

            # Fetch the XHTML document
            xhtml_response = requests.get(xhtml_url, headers=HEADERS, timeout=10)
            xhtml_response.raise_for_status()

            # Save to a temporary file for parsing
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xhtml") as temp_file:
                temp_file.write(xhtml_response.content)
                temp_file_path = temp_file.name

            logger.info(f"✅ Successfully downloaded XHTML document to {temp_file_path}")

            # Parse the XHTML file
            parse_and_save_financial_statement(temp_file_path, company.company_number)

            # Remove temp file after parsing
            os.remove(temp_file_path)

            processed_count += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching XHTML document for company {company.company_number}: {e}")
            continue  # Skip to next company

        time.sleep(sleep_time)  # Rate limit

    logger.info(f"🎉 Finished processing {processed_count} financial statements.")


def parse_date(date_str):
    """Converts various date formats into YYYY-MM-DD."""
    if not date_str:
        return None

    date_formats = ["%d.%m.%y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"]  # Common formats
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime("%Y-%m-%d")  # Convert to YYYY-MM-DD
        except ValueError:
            continue  # Try the next format

    logger.error(f"⚠️ Date format unknown: {date_str}")
    return None  # Return None if no format matches

def parse_and_save_financial_statement(file_path, company_number):
    """
    Parses an XHTML financial statement, extracts relevant financial metrics,
    and saves the data into the database.
    """
    logger.info(f"📄 Parsing financial statement from {file_path} for company {company_number}")

    # Parse the XML file
    try:
        with open(file_path, "rb") as f:
            tree = etree.parse(f)
    except Exception as e:
        logger.error(f"❌ Error parsing file {file_path}: {e}")
        return

    root = tree.getroot()
    namespaces = root.nsmap.copy()  # Get all namespaces
    logger.debug(f"🗂️ Detected XML Namespaces: {namespaces}")

    # Ensure required namespaces are present
    if None in namespaces:
        namespaces["default"] = namespaces.pop(None)
    if "ix" not in namespaces:
        namespaces["ix"] = "http://www.xbrl.org/2013/inlineXBRL"

    # Function to determine the prefix for a given XBRL standard
    def get_xbrl_prefix(standard_key):
        for prefix, uri in namespaces.items():
            if uri in XBRL_STANDARDS.get(standard_key, []):
                return prefix
        return None

    # Detect prefixes for core and business (bus)
    core_prefix = get_xbrl_prefix("core")
    bus_prefix = get_xbrl_prefix("bus")

    if not core_prefix and not bus_prefix:
        logger.warning("⚠️ No matching XBRL standard found. Falling back to table-based extraction.")

    # Function to clean extracted numbers
    def clean_number(value):
        if value in ["-", "", "N/A"]:
            return None
        try:
            value = value.replace(",", "").strip()
            return Decimal(value) if value else None
        except (InvalidOperation, ValueError):
            logger.error(f"❌ Could not convert value '{value}' to Decimal.")
            return None

    # Function to extract values dynamically (if XBRL namespaces are found)
    def get_value(tag, prefix):
        """Extracts values from inline XBRL if available, otherwise returns None."""
        if not prefix or not tag:
            return None

        xpath_query = None
        if prefix == core_prefix:
            xpath_query = f"//ix:nonFraction[@name='{prefix}:{tag}']"
        elif prefix == bus_prefix:
            xpath_query = f"//ix:hidden/ix:nonNumeric[@name='{prefix}:{tag}']"

        if xpath_query:
            try:
                elements = tree.xpath(xpath_query, namespaces=namespaces)
                if elements:
                    element = elements[0]
                    value = element.text.strip().replace(",", "")  # Clean the text value
                    logger.debug(f"🔍 Extracted `{tag}` from XBRL: {value}")

                    if prefix == core_prefix:
                        value = float(value)  # Convert to float
                        sign = element.get("sign")
                        if sign == "-":
                            value = -value  # Apply sign transformation
                    return value
            except etree.XPathEvalError as e:
                logger.error(f"⚠️ XPath error for `{tag}`: {e}")
            except Exception as e:
                logger.error(f"❌ Error running XPath query '{xpath_query}': {e}")

        logger.warning(f"⚠️ `{tag}` not found in XBRL. Trying table extraction...")
        return None  # Return None if no value was found



    # Fallback: Extract financial values from tables if no XBRL data is found
    def extract_value_from_table(label):
        """
        Extracts a value from an `iris_table` HTML table based on row labels.
        """
        try:
            # Find table rows containing the specified label (e.g., "TURNOVER")
            rows = tree.xpath(f"//tr[contains(@class, 'iris_table_row')]", namespaces=namespaces)

            for row in rows:
                cells = row.xpath(".//td")  # Get all cells in the row
                if len(cells) < 2:
                    continue  # Skip invalid rows
                
                row_label = cells[0].text_content().strip().upper()
                if label.upper() in row_label:
                    raw_value = cells[1].text_content().strip().replace(",", "")  # Get number value
                    logger.info(f"📊 Extracted `{label}` from table: {raw_value}")
                    return float(raw_value) if raw_value.replace('.', '', 1).isdigit() else None
        except Exception as e:
            logger.error(f"❌ Error extracting `{label}` from table: {e}")
        
        return None  # If no match is found


    # Fetch the company record
    company = Company.objects.filter(company_number=company_number).first()
    if not company:
        logger.error(f"❌ Company with number {company_number} not found.")
        return

    # Map extracted data to Django model fields
    financial_data = {
    "company_number": company.company_number,
    "company_name": company.company_name,
    "sic_code_1": company.sic_code_1,
    "report_end_date": parse_date(
        get_value("EndDateForPeriodCoveredByReport", bus_prefix) or extract_value_from_table("End of period")
    ),
    "average_employees": get_value("AverageNumberEmployeesDuringPeriod", core_prefix) or extract_value_from_table("Average number employees"),
    "turnover_revenue": get_value("TurnoverRevenue", core_prefix) or extract_value_from_table("TURNOVER"),
    "cost_of_sales": get_value("CostSales", core_prefix) or extract_value_from_table("Cost of sales"),
    "gross_profit_loss": get_value("GrossProfitLoss", core_prefix) or extract_value_from_table("GROSS PROFIT"),
    "distribution_costs": get_value("DistributionCosts", core_prefix) or extract_value_from_table("Distribution costs"),
    "administrative_expenses": get_value("AdministrativeExpenses", core_prefix) or extract_value_from_table("Administrative expenses"),
    "operating_profit_loss": get_value("OperatingProfitLoss", core_prefix) or extract_value_from_table("OPERATING PROFIT"),
    "profit_before_tax": get_value("ProfitLossOnOrdinaryActivitiesBeforeTax", core_prefix) or extract_value_from_table("PROFIT BEFORE TAXATION"),
    "profit_loss": get_value("ProfitLoss", core_prefix) or extract_value_from_table("PROFIT FOR THE FINANCIAL YEAR"),
    "total_comprehensive_income": get_value("TotalComprehensiveIncome", core_prefix) or extract_value_from_table("TOTAL COMPREHENSIVE INCOME"),
}

    # Log extracted data
    logger.info(f"✅ Extracted financial data for company {company_number}: {financial_data}")

    # Insert or update data in the database
    try:
        with transaction.atomic():
            FinancialStatement.objects.update_or_create(
                company_number=financial_data["company_number"],
                defaults=financial_data
            )
        logger.info(f"🎉 Successfully saved financial statement for {company_number}")
    except Exception as e:
        logger.error(f"❌ Error saving financial statement for {company_number}: {e}")
