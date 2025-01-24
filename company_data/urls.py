from django.urls import path
from .views import company_filter_view, home_view, company_detail_view, available_sic_codes_view

urlpatterns = [
    path('', home_view, name='home'),
    path('filter-companies/', company_filter_view, name='filter_companies'),
     path('company-detail/', company_detail_view, name='company_detail'),
     path('available-sic-codes/', available_sic_codes_view, name='available_sic_codes'),
]
