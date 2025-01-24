from django.db import models

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
    company_status = models.CharField(max_length=100, null=True, blank=True)
    country_of_origin = models.CharField(max_length=100, null=True, blank=True)
    dissolution_date = models.DateField(null=True, blank=True)
    incorporation_date = models.DateField(null=True, blank=True)
    accounts_account_ref_day = models.IntegerField(null=True, blank=True)
    accounts_account_ref_month = models.IntegerField(null=True, blank=True)
    accounts_next_due_date = models.DateField(null=True, blank=True)
    accounts_last_made_up_date = models.DateField(null=True, blank=True)
    accounts_account_category = models.CharField(max_length=100, null=True, blank=True)
    returns_next_due_date = models.DateField(null=True, blank=True)
    returns_last_made_up_date = models.DateField(null=True, blank=True)
    mortgages_num_mort_charges = models.IntegerField(null=True, blank=True)
    mortgages_num_mort_outstanding = models.IntegerField(null=True, blank=True)
    mortgages_num_mort_part_satisfied = models.IntegerField(null=True, blank=True)
    mortgages_num_mort_satisfied = models.IntegerField(null=True, blank=True)
    sic_code_1 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_2 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_3 = models.CharField(max_length=255, null=True, blank=True)
    sic_code_4 = models.CharField(max_length=255, null=True, blank=True)
    limited_partnerships_num_gen_partners = models.IntegerField(null=True, blank=True)
    limited_partnerships_num_lim_partners = models.IntegerField(null=True, blank=True)
    uri = models.URLField(null=True, blank=True)
    conf_stmt_next_due_date = models.DateField(null=True, blank=True)
    conf_stmt_last_made_up_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.company_name

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