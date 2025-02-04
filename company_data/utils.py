from django.db import transaction
from lxml import etree
from company_data.models import FinancialStatement, Company

def parse_and_save_financial_statement(file_path, company_number):
    print('running parse_and_save_financial_statement', file_path, company_number)
    with open(file_path, "r", encoding="utf-8") as f:
        tree = etree.parse(f)

    # Define namespaces for XPath queries
    namespaces = {
        "ix": "http://www.xbrl.org/2013/inlineXBRL",
        "e": "http://xbrl.frc.org.uk/fr/2021-01-01/core",
        "g": "http://xbrl.frc.org.uk/reports/2021-01-01/aurep",
        "h": "http://xbrl.frc.org.uk/reports/2021-01-01/direp"
    }

    # Fetch the company record
    company = Company.objects.filter(company_number=company_number).first()
    if not company:
        print(f"Company with number {company_number} not found.")
        return

    # Extract financial data dynamically
    def get_value(tag):
        element = tree.xpath(f"//ix:nonFraction[@name='{tag}']", namespaces=namespaces)
        return element[0].text.strip().replace(",", "") if element else None

    # Map extracted data to Django model fields
    financial_data = {
        "company_number": company.company_number,
        "company_name": company.company_name,
        "sic_code_1": company.sic_code_1,
        "reg_address_county": company.reg_address_county,
        "reg_address_postcode": company.reg_address_postcode,
        "average_employees": get_value("e:AverageNumberEmployeesDuringPeriod"),
        "turnover_revenue": get_value("e:TurnoverRevenue"),
        "cost_of_sales": get_value("e:CostSales"),
        "gross_profit_loss": get_value("e:GrossProfitLoss"),
        "distribution_costs": get_value("e:DistributionCosts"),
        "administrative_expenses": get_value("e:AdministrativeExpenses"),
        "other_operating_income": get_value("e:OtherOperatingIncomeFormat1"),
        "operating_profit_loss": get_value("e:OperatingProfitLoss"),
        "interest_payable": get_value("e:InterestPayableSimilarChargesFinanceCosts"),
        "profit_before_tax": get_value("e:ProfitLossOnOrdinaryActivitiesBeforeTax"),
        "tax_credit": get_value("e:TaxTaxCreditOnProfitOrLossOnOrdinaryActivities"),
        "profit_loss": get_value("e:ProfitLoss"),
        "property_plant_equipment": get_value("e:PropertyPlantEquipment"),
        "investment_property": get_value("e:InvestmentProperty"),
        "fixed_assets": get_value("e:FixedAssets"),
        "total_inventories": get_value("e:TotalInventories"),
        "debtors": get_value("e:Debtors"),
        "cash_at_bank": get_value("e:CashBankOnHand"),
        "current_assets": get_value("e:CurrentAssets"),
        "creditors": get_value("e:Creditors"),
        "net_current_assets_liabilities": get_value("e:NetCurrentAssetsLiabilities"),
        "total_assets_less_liabilities": get_value("e:TotalAssetsLessCurrentLiabilities"),
        "net_assets_liabilities": get_value("e:NetAssetsLiabilities"),
        "equity": get_value("e:Equity"),
        "taxation_provisions": get_value("e:TaxationIncludingDeferredTaxationBalanceSheetSubtotal"),
        "depreciation_rate": get_value("e:DepreciationRateUsedForPropertyPlantEquipment"),
        "wages_salaries": get_value("e:WagesSalaries"),
        "director_remuneration": get_value("h:DirectorRemuneration"),
        "director_pension_contributions": get_value("h:CompanyContributionsToMoneyPurchasePlansDirectors"),
    }

    # Insert or update data in the database
    with transaction.atomic():
        FinancialStatement.objects.update_or_create(
            company_number=financial_data["company_number"], defaults=financial_data
        )

    print(f"Successfully saved financial statement for {company_number}")
