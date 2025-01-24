from django.db.models import Q
from django.shortcuts import render
from django import forms
from django.core.paginator import Paginator
from company_data.models import Company, CompanyFiles

class CompanyFilterForm(forms.Form):
    accounts_next_due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False,
        label="Accounts Next Due Date (greater than)"
    )
    accounts_account_category = forms.MultipleChoiceField(
        required=False,
        widget=forms.SelectMultiple,
        label="Account Category",
        choices=[],  # Initially empty, populated dynamically in the view
    )
    sic_code_1 = forms.MultipleChoiceField(
        choices=[],
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="SIC Codes"
    )


def home_view(request):
    return render(request, 'company_data/home.html')


def available_sic_codes_view(request):
    unique_sic_codes = Company.objects.values_list('sic_code_1', flat=True).distinct()
    return render(request, 'company_data/available_sic_codes.html', {
        'unique_sic_codes': unique_sic_codes,
    })

def company_filter_view(request):
    # Get unique values for dropdowns
    unique_categories = Company.objects.values_list('accounts_account_category', flat=True).distinct()
    unique_sic_codes = Company.objects.values_list('sic_code_1', flat=True).distinct()

    form = CompanyFilterForm(request.GET or None)
    form.fields['accounts_account_category'].choices = [(cat, cat) for cat in unique_categories if cat]
    form.fields['sic_code_1'].choices = [(sic, sic) for sic in unique_sic_codes if sic]

    filtered_count = 0  # Default count is 0
    filtered_companies = []  # Default is an empty list

    if form.is_valid():
        accounts_next_due_date = form.cleaned_data.get('accounts_next_due_date')
        selected_categories = form.cleaned_data.get('accounts_account_category')
        selected_sic_codes = form.cleaned_data.get('sic_code_1')

        # Build the query dynamically
        filters = Q(company_status='Active')
        if accounts_next_due_date:
            filters &= Q(accounts_next_due_date__gt=accounts_next_due_date)
        if selected_categories:
            filters &= Q(accounts_account_category__in=selected_categories)
        if selected_sic_codes:
            filters &= Q(sic_code_1__in=selected_sic_codes)

        filtered_companies = Company.objects.filter(filters)
        filtered_count = filtered_companies.count()

    # Pagination
    paginator = Paginator(filtered_companies, 10)  # Show 10 companies per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'company_data/company_filter.html', {
        'form': form,
        'filtered_count': filtered_count,
        'filtered_companies': filtered_companies,
        'page_obj': page_obj,
        'unique_categories': unique_categories,
        'unique_sic_codes': unique_sic_codes,
    })



def company_detail_view(request):
    company = None
    company_files = []
    error = None
    company_number = request.GET.get('company_number')

    if company_number:
        try:
            company = Company.objects.get(company_number=company_number)
            company_files = CompanyFiles.objects.filter(company_number=company_number)
        except Company.DoesNotExist:
            error = f"No company found with company number: {company_number}"
    
    return render(request, 'company_data/company_detail.html', {
        'company': company,
        'company_files': company_files,
        'error': error,
    })