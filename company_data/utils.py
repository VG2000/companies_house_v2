from django.db import transaction
import logging
from datetime import datetime
import pandas as pd
import zipfile
import mimetypes
import os
from lxml import etree
from company_data.models import FinancialStatement, Company

# Configure logging
logger = logging.getLogger("company_data")

def parse_date(date_value):
    """
    Converts various date formats into '%Y-%m-%d' (ISO format).
    Handles:
      - Strings in UK format (DD/MM/YYYY) or ISO (YYYY-MM-DD)
      - Integers (Excel serial numbers) by converting to dates
      - Strings that contain numeric dates (e.g., "42518")
    Returns None if the value is invalid.
    """
    if pd.isna(date_value) or date_value is None:
        return None  # Handle empty or NaN values

    # ✅ Convert numeric strings to integers before processing
    if isinstance(date_value, str) and date_value.isdigit():
        date_value = int(date_value)  # Convert to integer

    # ✅ Handle Excel serial numbers (integers or floats)
    if isinstance(date_value, (int, float)):
        try:
            # Convert Excel serial number to proper date
            return (datetime(1899, 12, 30) + pd.to_timedelta(date_value, unit='D')).date()
        except Exception as e:
            print(f"⚠️ Warning: Cannot convert integer date {date_value} - {e}")
            return None

    # ✅ Handle string-based date formats
    if isinstance(date_value, str):
        date_formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]  # UK and ISO formats

        for fmt in date_formats:
            try:
                return datetime.strptime(date_value.strip(), fmt).date()
            except ValueError:
                continue  # Try the next format

    # 🚨 If no format matches, log a warning
    print(f"⚠️ Warning: Unrecognized date format: {date_value}")
    return None  # Return None for invalid dates




def parse_and_save_financial_statement(file_path, company_number):
    print(f"Parsing financial statement from {file_path} for company {company_number}")

    # Parse the XML file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = etree.parse(f)
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return

    # Dynamically detect namespaces from the document
    root = tree.getroot()
    namespaces = root.nsmap.copy()  # Get all namespaces
    print("Namespaces detected:", namespaces)

    # Ensure required namespaces are present
    if None in namespaces:
        namespaces["default"] = namespaces.pop(None)
    if "ix" not in namespaces:
        print("It can't find the ix namespace!")
        namespaces["ix"] = "http://www.xbrl.org/2013/inlineXBRL"

     # Known XBRL standards for both `core` and `bus`
    xbrl_standards = {
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

    # Function to determine the prefix for a given XBRL standard
    def get_xbrl_prefix(standard_key):
        for prefix, uri in namespaces.items():
            if uri in xbrl_standards.get(standard_key, []):
                return prefix
        return None

    # Detect prefixes for core and bus
    core_prefix = get_xbrl_prefix("core")
    bus_prefix = get_xbrl_prefix("bus")

    if not core_prefix and not bus_prefix:
        logger.error("No matching XBRL standard found in the namespaces.")
        return

    print(f"Using core prefix: {core_prefix}, bus prefix: {bus_prefix}")

    # Function to dynamically extract data
    def get_value(tag, prefix):
        """
        Extracts the value for a given tag, dynamically handling namespaces.
        Checks the 'sign' attribute only if the prefix is core_prefix.
        """
        xpath_query = None  # Initialize xpath_query to avoid undefined variable errors

        if prefix and tag:
            # Build the XPath query based on the prefix
            if prefix == core_prefix:
                xpath_query = f"//ix:nonFraction[@name='{prefix}:{tag}']"
            elif prefix == bus_prefix:
                xpath_query = f"//ix:hidden/ix:nonNumeric[@name='{prefix}:{tag}']"
            else:
                logger.error(f"Error! prefix: {prefix} tag: {tag} problem for company: {company_number}")

            if xpath_query:
                try:
                    # Find the element using XPath
                    elements = tree.xpath(xpath_query, namespaces=namespaces)
                    if elements:
                        element = elements[0]
                        value = element.text.strip().replace(",", "")  # Get the text value and clean it
                       

                        # Check the 'sign' attribute only if prefix == core_prefix
                        if prefix == core_prefix:
                            value = float(value)  # Convert to float for calculations
                            sign = element.get("sign")
                            if sign == "-":
                                value = -value  # Flip the sign of the value

                        return value
                except etree.XPathEvalError as e:
                    logger.error(f"XPath evaluation error: {e}")
                except Exception as e:
                    logger.error(f"Error running XPath query '{xpath_query}': {e}")

        # Return None if prefix or tag is missing or no match is found
        return None



    # Fetch the company record
    company = Company.objects.filter(company_number=company_number).first()
    if not company:
        logger.error(f"Company with number {company_number} not found.")
        return

    # Map extracted data to Django model fields
    financial_data = {
        "company_number": company.company_number,
        "company_name": company.company_name,
        "sic_code_1": company.sic_code_1,
        "reg_address_county": company.reg_address_county,
        "reg_address_postcode": company.reg_address_postcode,
        "reg_address_line1": company.reg_address_line1,
        "reg_address_line2": company.reg_address_line2,
        "reg_address_post_town": company.reg_address_post_town,
        "report_end_date": parse_date(get_value("EndDateForPeriodCoveredByReport", bus_prefix)),
        "average_employees": get_value("AverageNumberEmployeesDuringPeriod",core_prefix ),
        "turnover_revenue": get_value("TurnoverRevenue",core_prefix ),
        "cost_of_sales": get_value("CostSales",core_prefix ),
        "gross_profit_loss": get_value("GrossProfitLoss", core_prefix ),
        "distribution_costs": get_value("DistributionCosts", core_prefix ),
        "administrative_expenses": get_value("AdministrativeExpenses", core_prefix ),
        "other_operating_income": get_value("OtherOperatingIncomeFormat1", core_prefix ),
        "operating_profit_loss": get_value("OperatingProfitLoss", core_prefix ),
        "interest_payable": get_value("InterestPayableSimilarChargesFinanceCosts",core_prefix ),
        "profit_before_tax": get_value("ProfitLossOnOrdinaryActivitiesBeforeTax", core_prefix ),
        "tax_credit": get_value("TaxTaxCreditOnProfitOrLossOnOrdinaryActivities", core_prefix ),
        "profit_loss": get_value("ProfitLoss", core_prefix ),
        "property_plant_equipment": get_value("PropertyPlantEquipment", core_prefix ),
        "investment_property": get_value("InvestmentProperty", core_prefix ),
        "fixed_assets": get_value("FixedAssets", core_prefix ),
        "total_inventories": get_value("TotalInventories", core_prefix ),
        "debtors": get_value("Debtors", core_prefix ),
        "cash_at_bank": get_value("CashBankOnHand", core_prefix ),
        "current_assets": get_value("CurrentAssets", core_prefix ),
        "creditors": get_value("Creditors", core_prefix ),
        "net_current_assets_liabilities": get_value("NetCurrentAssetsLiabilities", core_prefix ),
        "total_assets_less_liabilities": get_value("TotalAssetsLessCurrentLiabilities", core_prefix ),
        "net_assets_liabilities": get_value("NetAssetsLiabilities", core_prefix ),
        "equity": get_value("Equity", core_prefix ),
        "taxation_provisions": get_value("TaxationIncludingDeferredTaxationBalanceSheetSubtotal", core_prefix ),
        "depreciation_rate": get_value("DepreciationRateUsedForPropertyPlantEquipment", core_prefix ),
        "wages_salaries": get_value("WagesSalaries", core_prefix ),
        "director_remuneration": get_value("DirectorRemuneration", core_prefix ),
        "director_pension_contributions": get_value("CompanyContributionsToMoneyPurchasePlansDirectors", core_prefix ),
    }

    # Log the extracted data
    print(f"Extracted data for company {company_number}: {financial_data}")

    # Insert or update data in the database
    try:
        with transaction.atomic():
            FinancialStatement.objects.update_or_create(
                company_number=financial_data["company_number"], defaults=financial_data
            )
        logger.info(f"Successfully saved financial statement for {company_number}")
    except Exception as e:
        logger.error(f"Error saving financial statement for {company_number}: {e}")



