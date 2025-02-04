import logging
import json
import os
import mimetypes
from django.db.models import Q
from django.shortcuts import render
from django import forms
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from company_data.models import Company, CompanyFiles, UniqueValuesCache
from django.shortcuts import render
from django.http import JsonResponse
import requests
import base64
import logging
import json
import time
from company_data.models import Company, FinancialStatement
from company_data.utils import parse_and_save_financial_statement
from company_data.filters import FinancialStatementFilter


# Configure logging
logger = logging.getLogger("company_data")

API_KEY = "17c5f21f-c601-45af-825d-b7b8cafe95b2"
BASE_URL = "https://api.company-information.service.gov.uk"
AUTH_HEADER = f"Basic {base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')}"
HEADERS = {"Authorization": AUTH_HEADER}

# Define the folder where the documents should be stored outside the Docker container
SAVE_PATH = os.path.abspath("./statements")  # Saves to ./statements/

# Ensure the directory exists
os.makedirs(SAVE_PATH, exist_ok=True)

def download_last_full_statements(request):
    if request.method == "POST":
        try:
            logger.debug("Initiating download_last_full_statements")

            # Get companies with non-null and non-empty last_full_statement_url
            companies = Company.objects.exclude(last_full_statement_url__isnull=True).exclude(last_full_statement_url="")[:600]

            downloaded_count = 0
            sleep_time = 0.8  # Wait time between requests (to stay within rate limit)

            for company in companies:
                metadata_url = company.last_full_statement_url  # This is the metadata URL
                company_number = company.company_number

                if not metadata_url:
                    logger.warning(f"Skipping {company_number}: No last_full_statement_url found")
                    continue  # Skip if no URL is found

                 # Check if file already exists
                existing_files = [
                    f"{company_number}.xml",
                    f"{company_number}.xhtml",
                    f"{company_number}.pdf"
                ]
                if any(os.path.exists(os.path.join(SAVE_PATH, file)) for file in existing_files):
                    logger.info(f"Skipping {company_number}: File already exists in {SAVE_PATH}")
                    continue  # Skip downloading

                logger.info(f"Fetching document metadata for company {company_number} from {metadata_url}")

                try:
                    # Fetch the metadata JSON
                    response = requests.get(metadata_url, headers=HEADERS, timeout=10)
                    response.raise_for_status()

                    content_type = response.headers.get("Content-Type", "")

                    # If JSON is returned, extract document download URL
                    if "application/json" in content_type:
                        metadata = response.json()
                        logger.info(f"Metadata received for {company_number}: {metadata}")

                        # Extract document download links from "resources"
                        resources = metadata.get("resources", {})
                        xml_available = "application/xml" in resources
                        xhtml_available = "application/xhtml+xml" in resources
                        pdf_available = "application/pdf" in resources

                        # Prioritize XML > XHTML > PDF
                        if xml_available:
                            document_url = metadata["links"]["document"] 
                            file_extension = "xml"
                        elif xhtml_available:
                            document_url = metadata["links"]["document"]
                            file_extension = "xhtml"
                        elif pdf_available:
                            document_url = metadata["links"]["document"] 
                            file_extension = "pdf"
                        else:
                            logger.error(f"No downloadable document found for {company_number}")
                            continue

                        logger.info(f"Downloading {file_extension} document for {company_number} from {document_url}")

                        # Fetch the actual document
                        document_response = requests.get(document_url, headers=HEADERS, timeout=20)
                        document_response.raise_for_status()

                        # Define file path (Save in current directory for testing)
                        file_path = os.path.join(SAVE_PATH, f"{company_number}.{file_extension}")

                        # Save the file
                        logger.info(f"Attempting to save {file_extension} document for {company_number} at {file_path}")

                        with open(file_path, "wb") as file:
                            file.write(document_response.content)

                        # Verify if file exists after writing
                        if os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            mime_type, _ = mimetypes.guess_type(file_path)

                            logger.info(f"Successfully saved statement for {company_number} at {file_path}")
                            logger.info(f"File properties for {company_number}: Size = {file_size} bytes, MIME Type = {mime_type}")

                            downloaded_count += 1
                        else:
                            logger.error(f"Failed to save statement for {company_number}: File does not exist after writing")

                except requests.exceptions.RequestException as e:
                    logger.error(f"Error downloading statement for {company_number}: {e}")
                    continue

                # Sleep to comply with rate limit
                time.sleep(sleep_time)

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Successfully downloaded {downloaded_count} statements.",
                }
            )

        except Exception as e:
            logger.error(f"Error occurred while downloading statements: {e}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": "An error occurred while downloading statements."}
            )

    return JsonResponse({"status": "error", "message": "Invalid request method."})


def update_full_accounts_paper_filed(request):
    if request.method == "POST":
        try:
            logger.debug("Initiating update_full_accounts_paper_filed")
            companies = Company.objects.filter(current_full_accounts=True)
            updated_count = 0
            sleep_time = 0.6  # Wait time between requests (to stay within rate limit)

            for company in companies:
                company_number = company.company_number
                url = f"{BASE_URL}/company/{company_number}/filing-history"
                

                logger.debug(f"Fetching filing history for company: {company_number}")
                try:
                    response = requests.get(url, headers=HEADERS, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    # Parse the JSON to find the first key "type" with value "AA"
                    items = data.get("items", [])
                    for item in items:
                        if item.get("type") == "AA":
                            logger.info(f"Processing document metadata for company: {company_number}")

                            paper_filed = item.get("paper_filed", False)
                            if paper_filed == False:
                                # Fetch the document metadata URL
                                document_url = item.get("links", {}).get("document_metadata")
                                
                                if document_url:
                                    # Set the url for a later document fetch
                                    company.last_full_statement_url = document_url
                                    logger.info(f"Updated company {company_number}: last_full_statement_url={document_url}")
                                    company.full_accounts_paper_filed = paper_filed
                                    company.save()

                            updated_count += 1
                            logger.info(f"Updated company {company_number}: full_accounts_paper_filed={paper_filed}")
                            break

                except requests.exceptions.RequestException as e:
                    logger.error(f"Error fetching data for company {company_number}: {e}")
                    continue

                # Sleep to comply with rate limit
                time.sleep(sleep_time)

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Successfully updated {updated_count} companies.",
                }
            )
        except Exception as e:
            logger.error(f"Error occurred while updating companies: {e}", exc_info=True)
            return JsonResponse(
                {"status": "error", "message": "An error occurred while updating companies."}
            )

    return JsonResponse({"status": "error", "message": "Invalid request method."})


def show_update_full_accounts_page(request):
    full_accounts_count = Company.objects.filter(current_full_accounts=True).count()
    electronic_filings_count = Company.objects.exclude(last_full_statement_url__isnull=True).exclude(last_full_statement_url="").count()
    return render(request, 'company_data/update_company_filing_type.html', {'full_accounts_count': full_accounts_count, 'electronic_filings_count':electronic_filings_count})

def search_company(request):
    company_data = None
    error = None
    ip_address = get_client_ip(request)
    company_number = None
    data_type = "company_data"  # Default to Company Data

    if request.method == 'POST':
        company_number = request.POST.get('company_number')
        data_type = request.POST.get('data_type')

        # Determine the URL based on the selected option
        if data_type == "filing_history":
            url = f"{BASE_URL}/company/{company_number}/filing-history"
        else:  # Default to Company Data
            url = f"{BASE_URL}/company/{company_number}"

        logger.debug(f"Fetching data for company number: {company_number}")
        logger.debug(f"Selected option: {data_type}")
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request coming from IP: {ip_address}")

        # Construct the Authorization header
        auth_header = f"Basic {base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')}"
        headers = {"Authorization": auth_header}
        logger.debug(f"Authorization Header: {headers['Authorization']}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            # Format the JSON data nicely for display
            company_data = json.dumps(response.json(), indent=4)
        except requests.exceptions.Timeout:
            logger.error("The request to the API timed out.")
            error = "The request to the API timed out."
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            error = f"An error occurred while fetching data. {e}"

    return render(request, 'company_data/company_search.html', {
        'company_data': company_data,
        'error': error,
        'ip_address': ip_address,
        'company_number': company_number,
        'data_type': data_type
    })


def get_client_ip(request):
    """Get the client's IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



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
    try:
        # Fetch the cached unique SIC codes from UniqueValuesCache
        unique_sic_codes_cache = UniqueValuesCache.objects.get(key='unique_sic_codes')
        unique_sic_codes = unique_sic_codes_cache.values  # Retrieve the values field
    except UniqueValuesCache.DoesNotExist:
        # Fallback in case the cache is not available
        unique_sic_codes = []

    return render(request, 'company_data/available_sic_codes.html', {
        'unique_sic_codes': unique_sic_codes,
    })


def company_filter_view(request):
    logger.info("Entering company_filter_view")

    # Fetch unique categories and SIC codes from cache
    logger.info("Fetching unique categories and SIC codes from cache")
    try:
        unique_categories = UniqueValuesCache.objects.get(key='unique_categories').values
        unique_sic_codes = UniqueValuesCache.objects.get(key='unique_sic_codes').values
        logger.info(f"Fetched cached values - Unique categories: {len(unique_categories)}, Unique SIC codes: {len(unique_sic_codes)}")
    except UniqueValuesCache.DoesNotExist:
        # logger.warning("UniqueValuesCache not found; dynamically fetching unique values")
        # unique_categories = list(Company.objects.values_list('accounts_account_category', flat=True).distinct())
        # unique_sic_codes = list(Company.objects.values_list('sic_code_1', flat=True).distinct())
        logger.warning("UniqueValuesCache not found; returning empty lists")
        unique_categories = []
        unique_sic_codes = []

    # Initialize form
    logger.info("Initializing form with unique dropdown values")
    form = CompanyFilterForm(request.GET or None)
    form.fields['accounts_account_category'].choices = [(cat, cat) for cat in unique_categories if cat]
    form.fields['sic_code_1'].choices = [(sic, sic) for sic in unique_sic_codes if sic]

    filtered_count = 0
    filtered_companies = []
    page_obj = None

    # Check if filters are applied
    logger.info("Checking if filters are applied")
    if request.GET and form.is_valid():
        logger.info("Filters applied, validating form data")
        try:
            accounts_next_due_date = form.cleaned_data.get('accounts_next_due_date')
            selected_categories = form.cleaned_data.get('accounts_account_category')
            selected_sic_codes = form.cleaned_data.get('sic_code_1')

            logger.info(f"Filter criteria - accounts_next_due_date: {accounts_next_due_date}, "
                        f"selected_categories: {selected_categories}, selected_sic_codes: {selected_sic_codes}")

            # Build the filters dynamically
            filters = Q(company_status='Active')
            if accounts_next_due_date:
                filters &= Q(accounts_next_due_date__gt=accounts_next_due_date)
            if selected_categories:
                filters &= Q(accounts_account_category__in=selected_categories)
            if selected_sic_codes:
                filters &= Q(sic_code_1__in=selected_sic_codes)

            logger.info(f"Applying filters: {filters}")

            # Apply filters
            filtered_companies = Company.objects.filter(filters).order_by('company_name')
            filtered_count = filtered_companies.count()
            logger.info(f"Filtered companies count: {filtered_count}")

            # Pagination
            paginator = Paginator(filtered_companies, 10)  # Show 10 companies per page
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            logger.info(f"Pagination complete - Page number: {page_number}, Items on page: {len(page_obj)}")
        except Exception as e:
            logger.error(f"Error applying filters or pagination: {e}")

    # Render the template
    logger.info("Rendering the template")
    return render(request, 'company_data/company_filter.html', {
        'form': form,
        'filtered_count': filtered_count,
        'filtered_companies': filtered_companies,
        'page_obj': page_obj,
        'unique_categories': unique_categories,
        'unique_sic_codes': unique_sic_codes,
    })


@csrf_exempt
def update_current_full_accounts(request):
    if request.method == 'POST':
        try:
            logger.info("Received request to update current_full_accounts")

            # Parse filter parameters from the request body
            body = json.loads(request.body)
            logger.info(f"Received filter parameters: {body}")

            accounts_next_due_date = body.get('accounts_next_due_date')
            selected_categories = body.get('accounts_account_category', [])
            selected_sic_codes = body.get('sic_code_1', [])

            # Ensure selected_categories and selected_sic_codes are lists
            if isinstance(selected_categories, str):
                selected_categories = [selected_categories]
            if isinstance(selected_sic_codes, str):
                selected_sic_codes = [selected_sic_codes]

            logger.info(f"Parsed filter parameters - accounts_next_due_date: {accounts_next_due_date}, "
                        f"selected_categories: {selected_categories}, selected_sic_codes: {selected_sic_codes}")

            # Build the filters dynamically
            filters = Q(company_status='Active')
            if accounts_next_due_date:
                filters &= Q(accounts_next_due_date__gt=accounts_next_due_date)
            if selected_categories:
                filters &= Q(accounts_account_category__in=selected_categories)
            if selected_sic_codes:
                filters &= Q(sic_code_1__in=selected_sic_codes)

            # Log the constructed filter
            logger.info(f"Constructed filter: {filters}")

            # Check if the filters are restrictive enough
            matching_count = Company.objects.filter(filters).count()
            logger.info(f"Matching companies count before update: {matching_count}")

            if matching_count == 0:
                logger.warning("No matching records found for the given filters. Aborting update.")
                return JsonResponse({'status': 'error', 'message': 'No matching records found. Update aborted.'})

            # Safeguard: Do not update if no restrictive filters are applied
            if matching_count >= Company.objects.count():
                logger.error("Filters are too broad. Update would affect all records. Aborting.")
                return JsonResponse({'status': 'error', 'message': 'Filters are too broad. Update aborted.'})

            # Update matching companies
            updated_count = Company.objects.filter(filters).update(current_full_accounts=True)
            logger.info(f"Successfully updated {updated_count} companies")

            return JsonResponse({'status': 'success', 'message': f'Successfully updated {updated_count} companies.'})
        except Exception as e:
            logger.error(f"Error occurred while updating companies: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An error occurred while updating companies.'})
    else:
        logger.warning("Invalid request method")
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@csrf_exempt
def reset_current_full_accounts(request):
    if request.method == 'POST':
        try:
            logger.info("Received request to reset current_full_accounts for all companies")

            # Track start time for performance monitoring
            from datetime import datetime
            start_time = datetime.now()

            # Batch size for the update
            batch_size = 10000
            total_updated = 0

            logger.info(f"Starting batch reset for current_full_accounts in batches of {batch_size}")

            # Update in batches using primary keys
            while True:
                # Get primary keys of rows to update in the current batch
                batch_ids = list(
                    Company.objects.filter(current_full_accounts=True)
                    .values_list('id', flat=True)[:batch_size]
                )

                if not batch_ids:
                    break

                # Perform the update for the current batch
                updated_count = Company.objects.filter(id__in=batch_ids).update(current_full_accounts=False)
                total_updated += updated_count

                # Log progress
                logger.info(f"Batch updated: {updated_count} rows (Total updated: {total_updated})")

            # Track end time
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"Successfully reset current_full_accounts for {total_updated} companies in {duration.total_seconds()} seconds")

            return JsonResponse({'status': 'success', 'message': f'Successfully reset {total_updated} companies in {duration.total_seconds()} seconds.'})
        except Exception as e:
            logger.error(f"Error occurred while resetting companies: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': 'An error occurred while resetting companies.'})
    else:
        logger.warning("Invalid request method")
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


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

@csrf_exempt
def process_all_statements(request):
    """Iterates through all files in the statements folder and processes them."""
    if request.method == "POST":
        try:
            logger.info("Starting processing of all financial statements.")

            # Ensure the folder exists
            if not os.path.exists(SAVE_PATH):
                logger.error(f"Statements folder not found: {SAVE_PATH}")
                return JsonResponse({"status": "error", "message": "Statements folder not found."})

            # List all files in the statements folder
            files = [f for f in os.listdir(SAVE_PATH) if f.endswith(('.xml', '.xhtml'))]
            if not files:
                logger.warning("No financial statement files found.")
                return JsonResponse({"status": "warning", "message": "No financial statements to process."})

            processed_count = 0

            for file in files:
                file_path = os.path.join(SAVE_PATH, file)

                # Extract company number from filename (assumes format: <company_number>.<extension>)
                company_number = file.split('.')[0]

                logger.info(f"Processing file {file_path} for company {company_number}")

                try:
                    parse_and_save_financial_statement(file_path, company_number)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")

            return JsonResponse(
                {"status": "success", "message": f"Processed {processed_count} financial statements."}
            )

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": "An error occurred while processing statements."})

    return JsonResponse({"status": "error", "message": "Invalid request method."})


def financial_statements_list(request):
    """Filters and paginates financial statements."""
    # Filter the queryset using FinancialStatementFilter
    filtered_statements = FinancialStatementFilter(
        request.GET, 
        queryset=FinancialStatement.objects.all()
    )

    # Paginate the filtered queryset (25 items per page)
    paginator = Paginator(filtered_statements.qs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Render the template with the paginated data
    return render(request, "company_data/process_statements.html", {
        "financial_statements": page_obj if page_obj.object_list else None,  # Pass None if no records
        "page_obj": page_obj,
    })


