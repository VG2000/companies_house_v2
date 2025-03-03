from django.db import models

class Company(models.Model):
    company_name = models.CharField(max_length=255, null=True, blank=True)
    company_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    reg_address_care_of = models.CharField(max_length=255, null=True, blank=True)
    reg_address_po_box = models.CharField(max_length=50, null=True, blank=True)
    reg_address_line1 = models.CharField(max_length=255, null=True, blank=True)
    reg_address_line2 = models.CharField(max_length=255, null=True, blank=True)
    reg_address_post_town = models.CharField(max_length=255, null=True, blank=True)
    reg_address_county = models.CharField(max_length=255, null=True, blank=True)
    reg_address_country = models.CharField(max_length=255, null=True, blank=True)
    reg_address_postcode = models.CharField(max_length=50, null=True, blank=True)
    company_category = models.CharField(max_length=100, null=True, blank=True)
    company_status = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    country_of_origin = models.CharField(max_length=100, null=True, blank=True)
    dissolution_date = models.DateField(null=True, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    accounts_account_ref_day = models.IntegerField(null=True, blank=True)
    accounts_account_ref_month = models.IntegerField(null=True, blank=True)
    accounts_next_due_date = models.DateField(null=True, blank=True, db_index=True)
    accounts_last_made_up_date = models.DateField(null=True, blank=True)
    accounts_account_category = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    returns_next_due_date = models.DateField(null=True, blank=True)
    returns_last_made_up_date = models.DateField(null=True, blank=True)
    mortgages_num_mort_charges = models.IntegerField(null=True, blank=True)
    mortgages_num_mort_outstanding = models.IntegerField(null=True, blank=True)
    mortgages_num_mort_part_satisfied = models.IntegerField(null=True, blank=True)
    mortgages_num_mort_satisfied = models.IntegerField(null=True, blank=True)
    sic_code_1 = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    sic_code_2 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_3 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_4 = models.CharField(max_length=255, null=True, blank=True)
    limited_partnerships_num_gen_partners = models.IntegerField(null=True, blank=True)
    limited_partnerships_num_lim_partners = models.IntegerField(null=True, blank=True)
    uri = models.URLField(null=True, blank=True)
    conf_stmt_next_due_date = models.DateField(null=True, blank=True)
    conf_stmt_last_made_up_date = models.DateField(null=True, blank=True)
    current_full_accounts = models.BooleanField(null=True, blank=True, default=False, db_index=True) # DO NOT NEED THIS ANY MORE
    full_accounts_paper_filed = models.BooleanField(null=True, blank=True, default=True, db_index=True)
    last_full_statement_url = models.URLField(null=True, blank=True)

    class Meta:
        ordering = ['company_name']  # Default ordering for the model

    def __str__(self):
        return f"{self.company_name or 'Unknown Company'} ({self.company_number or 'No Number'})"



# NOT SURE I NEED THIS MODEL?============================================================
class CompanyFiles(models.Model):
    file_url = models.URLField() 
    process_number = models.CharField(max_length=20)
    company_number = models.CharField(max_length=20)
    balance_sheet_date = models.DateField()
    file_type = models.CharField(max_length=5)
    
    def __str__(self):
        return self.file_url
    
    class Meta:
        verbose_name = "Company file"
        verbose_name_plural = "Company files"


class UniqueValuesCache(models.Model):
    key = models.CharField(max_length=255, unique=True)
    values = models.JSONField()

    def __str__(self):
        return self.key

class FinancialStatement(models.Model):
    # Store necessary fields from the Company model
    company_number = models.CharField(max_length=50, db_index=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    sic_code_1 = models.CharField(max_length=255, null=True, blank=True)
    reg_address_county = models.CharField(max_length=255, null=True, blank=True)
    reg_address_postcode = models.CharField(max_length=50, null=True, blank=True)
    reg_address_line1 = models.CharField(max_length=255, null=True, blank=True)
    reg_address_line2 = models.CharField(max_length=255, null=True, blank=True)
    reg_address_post_town = models.CharField(max_length=255, null=True, blank=True)

    # Meta Data
    report_end_date = models.DateField(null=True, blank=True)

    # Balance Sheet
    average_employees = models.IntegerField(null=True, blank=True)
    turnover_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    cost_of_sales = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    gross_profit_loss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    distribution_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    administrative_expenses = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    other_operating_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    operating_profit_loss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    interest_payable = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    profit_before_tax = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_credit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    profit_loss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Assets
    property_plant_equipment = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    investment_property = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fixed_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_inventories = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    debtors = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    cash_at_bank = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Liabilities
    creditors = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_current_assets_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_assets_less_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_assets_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    equity = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Tax and Provisions
    taxation_provisions = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Revenue Sources
    revenue_from_sales = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    rental_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    government_grant_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Expenses
    wages_salaries = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    social_security_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pension_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    staff_costs = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Directors
    director_remuneration = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    director_pension_contributions = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Financial Statement for {self.company_number} - {self.company_name}"

    class Meta:
        verbose_name = "Financial Statement"
        verbose_name_plural = "Financial Statements"
        

class CompanyOfInterest(models.Model):
    company_number = models.CharField(max_length=50, db_index=True, unique=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    sic_code_1 = models.CharField(max_length=255, null=True, blank=True)


class SicDivision(models.Model):
    code = models.CharField(max_length=5, unique=True, db_index=True)
    description = models.TextField()

    def __str__(self):
        return f"{self.code}: {self.description}"
    
    class Meta:
        verbose_name = "SIC Division"
        verbose_name_plural = "SIC Divisions"
        ordering = ["code"]


class SicGroup(models.Model):
    code = models.CharField(max_length=5, unique=True, db_index=True)
    division = models.ForeignKey(SicDivision, on_delete=models.CASCADE, related_name="groups")
    description = models.TextField()

    def __str__(self):
        return f"{self.code}: {self.description} (Division {self.division.code})"
    
    class Meta:
        verbose_name = "SIC Group"
        verbose_name_plural = "SIC Groups"
        ordering = ["code"]


class SicClass(models.Model):
    code = models.CharField(max_length=5, unique=True, db_index=True)
    group = models.ForeignKey(SicGroup, on_delete=models.CASCADE, related_name="classes")
    division = models.ForeignKey(SicDivision, on_delete=models.CASCADE, related_name="classes")
    description = models.TextField()

    def __str__(self):
        return f"{self.code}: {self.description} (Group {self.group.code})"
    
    class Meta:
        verbose_name = "SIC Class"
        verbose_name_plural = "SIC Classes"
        ordering = ["code"]


class FinancialMetrics(models.Model):
    # Income Statement Fields
    TurnoverRevenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    CostSales = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    GrossProfitLoss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ProfitLoss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    AdministrativeExpenses = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    OtherOperatingIncomeFormat1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    OperatingProfit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    OperatingProfitLoss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    OtherInterestRecievablesSimilarIncomeFinanceIncome = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ProfitLossOnOrdinaryActivitiesBeforeTax = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    TaxTaxCreditOnProfitOrLossOnOrdinaryActivities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    NetIncome = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    GrossProfit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Balance Sheet Fields
    IntangibleAssets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    PropertyPlantEquipment = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    InvestmentsFixedAssets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    FixedAssets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    TotalInventories = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    Debtors = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    CashBankOnHand = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    CurrentAssets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    TotalAssetsLessCurrentLiabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    Creditors = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    TaxationIncludingDeferredTaxationBalanceSheetSubtotal = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    NetCurrentAssetsLiabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    NetAssetsLiabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Cash Flow Statement Fields
    NetCashFlowsFromUsedInOperatingActivities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    NetCashFlowsFromUsedInInvestingActivities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    CashCashEquivalents = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    IncreaseDecreaseInCashCashEquivalents = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Metadata
    company_number = models.CharField(max_length=20, unique=True)
    filing_date = models.DateField(null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    sic_code_1 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_2 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_3 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_4 = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=50, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    locality = models.CharField(max_length=255, null=True, blank=True)
    

    def __str__(self):
        return f"Financial Metrics for Company {self.company_number} ({self.filing_date})"

    class Meta:
        verbose_name_plural = "Financial Metrics"


class ITLLevel1(models.Model):
    """International Territorial Level 1 (Highest Level)"""
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "ITL Level 1"
        verbose_name_plural = "ITL Level 1"


class ITLLevel2(models.Model):
    """ITL Level 2 (Sub-level of ITL1)"""
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    itl1 = models.ForeignKey(ITLLevel1, on_delete=models.CASCADE, related_name="itl2_regions")

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "ITL Level 2"
        verbose_name_plural = "ITL Level 2"    

class ITLLevel3(models.Model):
    """ITL Level 3 (Sub-level of ITL1)"""
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    itl2 = models.ForeignKey(ITLLevel2, on_delete=models.CASCADE, related_name="itl3_regions")

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "ITL Level 3"
        verbose_name_plural = "ITL Level 3"


class LocalAdministrativeUnit(models.Model):
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    itl3 = models.ForeignKey(ITLLevel3, on_delete=models.CASCADE, related_name="lau", null=True, blank=True)  # TEMP ALLOW NULL

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "Local Admin Unit"
        verbose_name_plural = "Local Admin Units"



class Postcode(models.Model):
    code = models.CharField(max_length=10, unique=True, db_index=True)
    district = models.ForeignKey(
        "company_data.LocalAdministrativeUnit", on_delete=models.CASCADE, related_name="postcodes"
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} ({self.district})"
    
    class Meta:
        verbose_name = "Postcode"
        verbose_name_plural = "Postcodes"
