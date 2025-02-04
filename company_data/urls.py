from django.urls import path
from .views import (company_filter_view, home_view, 
                    company_detail_view, 
                    available_sic_codes_view, 
                    update_current_full_accounts,
                    reset_current_full_accounts,
                    search_company,
                    update_full_accounts_paper_filed,
                    show_update_full_accounts_page,
                    download_last_full_statements,
                    process_all_statements,
                    financial_statements_list,
                    )

urlpatterns = [
    path('', home_view, name='home'),
    path('search-company', search_company, name='search_company'),
    path('filter-companies/', company_filter_view, name='filter_companies'),
    path('company-detail/', company_detail_view, name='company_detail'),
    path('available-sic-codes/', available_sic_codes_view, name='available_sic_codes'),
    path('update-current-full-accounts/', update_current_full_accounts, name='update_current_full_accounts'),
    path('reset-current-full-accounts/', reset_current_full_accounts, name='reset_current_full_accounts'),
    path('update-full-accounts/', update_full_accounts_paper_filed, name='update_full_accounts_paper_filed'),
    path('download-last-full-accounts/', download_last_full_statements, name='download_last_full_statements'),
    path('update-file-type/', show_update_full_accounts_page, name='show_update_full_accounts_page'),
    path("process-statements/", process_all_statements, name="process_statements"),
    path("financial-statements/", financial_statements_list, name="financial_statements_list"),
]

