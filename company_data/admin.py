from django.contrib import admin, messages
from .models import (
    Company, 
    CompanyFiles, 
    UniqueValuesCache, 
    FinancialStatement, 
    CompanyOfInterest,
    SicClass,
    SicDivision,
    SicGroup,
    )
from django.urls import path
from django.http import HttpResponseRedirect
from django.urls import reverse

class CompanyAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'company_number', 'current_full_accounts','full_accounts_paper_filed')
    list_filter = ('current_full_accounts','full_accounts_paper_filed',"company_status", "accounts_account_category")
    search_fields = ('company_name', 'company_number')

class UniqueValuesCacheAdmin(admin.ModelAdmin):
    change_list_template = "admin/uniquevaluescache_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'precompute-unique-values/',
                self.admin_site.admin_view(self.precompute_unique_values),
                name='precompute_unique_values',
            ),
        ]
        return custom_urls + urls

    def precompute_unique_values(self, request):
        try:
            unique_categories = list(Company.objects.values_list('accounts_account_category', flat=True).distinct())
            unique_sic_codes = list(Company.objects.values_list('sic_code_1', flat=True).distinct())

            UniqueValuesCache.objects.update_or_create(key='unique_categories', defaults={'values': unique_categories})
            UniqueValuesCache.objects.update_or_create(key='unique_sic_codes', defaults={'values': unique_sic_codes})

            self.message_user(request, "Unique values successfully precomputed and stored.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"An error occurred: {e}", messages.ERROR)

        return HttpResponseRedirect(reverse('admin:company_data_uniquevaluescache_changelist'))


# Register your models here.
admin.site.register(Company, CompanyAdmin)
admin.site.register(UniqueValuesCache, UniqueValuesCacheAdmin)
admin.site.register(CompanyFiles)
admin.site.register(FinancialStatement)
admin.site.register(CompanyOfInterest)
admin.site.register(SicDivision)
admin.site.register(SicGroup)
admin.site.register(SicClass)

# Customize the admin site title
admin.site.site_header = "Jackson Sq Admin"
admin.site.site_title = "Jackson Sq Admin Portal"
admin.site.index_title = "Welcome to Jackson Sq Administration"


