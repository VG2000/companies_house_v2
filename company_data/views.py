import logging
import json
import os
import mimetypes
from django.db.models import Q
from django.core.cache import cache
from django.shortcuts import render
from django import forms
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from company_data.models import Company, CompanyFiles, UniqueValuesCache
from django.shortcuts import render
from django.http import JsonResponse
from django.apps import apps
import requests
import base64
import logging
import json
import time
from company_data.models import Company, FinancialStatement, CompanyOfInterest, SicClass, SicDivision, SicGroup
from company_data.utils import parse_and_save_financial_statement



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

def statement_admin(request):
    return render(request, 'company_data/statement_admin.html')


def get_first_aa_document_url(response):
    """
    Extracts the document_metadata URL for the first filing history item with type "AA".
    """
    try:
        filing_history = response.json()  # Parse the response JSON
        items = filing_history.get("items", [])
        for item in items:
            if item.get("type") == "AA":  # Find the first "type": "AA"
                document_metadata = item.get("links", {}).get("document_metadata")
                if document_metadata:
                    return f"{document_metadata}" 
        return None
    except Exception as e:
        logger.error(f"Error extracting document URL: {e}")
        return None

  

def get_last_full_statement_file_type(request):

    if request.method == "POST":
        try:
            logger.debug("Initiating download_last_full_statements")
            sleep_time = 0.8  # Wait time between requests (to stay within rate limit)
            # Get companies with non-null and non-empty last_full_statement_url
            companies = Company.objects.exclude(last_full_statement_url__isnull=True).exclude(last_full_statement_url="")[:400]
            # company_number='00056547'
            # companies = Company.objects.filter(
            #     company_number=company_number
            # )
            count_co = companies.count()

            print("Number of companies: ",count_co)

            # logger.info(f"Fetching document metadata for company {company_number} from {metadata_url}")

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
                        file_extension = ''
                        document_url = ''


                        # Prioritize XML > XHTML > PDF
                        if xml_available:
                            document_url = metadata["links"]["document"] 
                            file_extension = "xml"
                            accept_header = "application/xml"
                        elif xhtml_available:
                            document_url = metadata["links"]["document"]
                            file_extension = "xhtml"
                            accept_header = "application/xhtml+xml"
                        elif pdf_available:
                            document_url = metadata["links"]["document"] 
                            file_extension = "pdf"
                            accept_header = "application/pdf"
                        else:
                            logger.error(f"No downloadable document found for {company_number}")
                            continue

                        logger.info(f"Downloading {file_extension} document for {company_number} from {document_url}")
                        
                         # Set headers dynamically
                        headers = {"Authorization": AUTH_HEADER,
                            "Accept": accept_header,  # Dynamically set the Accept header based on file type
                        }

                        try:
                            logger.info(f"Attempting to download {file_extension} document for {company_number} from {document_url}")
                            document_response = requests.get(document_url, headers=headers, timeout=20)
                            document_response.raise_for_status()

                            # Get the actual Content-Type from the response
                            content_type = document_response.headers.get("Content-Type", "").lower()
                            logger.info(f"Downloaded file Content-Type: {content_type}")

                            # Map Content-Type to expected extensions
                            mime_type_to_extension = {
                                "application/xhtml+xml": "xhtml",
                                "application/pdf": "pdf",
                            }

                            # Validate the Content-Type and adjust the file extension if necessary
                            if content_type in mime_type_to_extension:
                                actual_file_extension = mime_type_to_extension[content_type]
                                if actual_file_extension != file_extension:
                                    logger.warning(
                                        f"Expected file type {file_extension}, but got {actual_file_extension}. Adjusting file extension."
                                    )
                                    file_extension = actual_file_extension
                            else:
                                logger.error(
                                    f"Unexpected Content-Type '{content_type}' for {company_number}. Skipping download."
                                )
                                continue  # Skip processing if the Content-Type is unknown

                            # Save the file with the correct extension
                            file_path = os.path.join(SAVE_PATH, f"{company_number}.{file_extension}")
                            with open(file_path, "wb") as file:
                                file.write(document_response.content)
                            logger.info(f"Successfully saved {file_extension} document for {company_number} at {file_path}")

                        except requests.exceptions.RequestException as e:
                            logger.error(f"Failed to download {file_extension} document for {company_number}: {e}")
                            continue

                except requests.exceptions.RequestException as e:
                    logger.error(f"Error downloading statement for {company_number}: {e}")
                    continue

        # Sleep to comply with rate limit
                time.sleep(sleep_time)
        except:
            pass

    return JsonResponse({"status": "success", "message": f"Number of companies: {count_co}"})


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
                            accept_header = "application/xml"
                        elif xhtml_available:
                            document_url = metadata["links"]["document"]
                            file_extension = "xhtml"
                            accept_header = "application/xhtml+xml"
                        elif pdf_available:
                            document_url = metadata["links"]["document"]
                            file_extension = "pdf"
                            accept_header = "application/pdf"
                        else:
                            logger.error(f"No downloadable document found for {company_number}")
                            continue

                        logger.info(f"Downloading {file_extension} document for {company_number} from {document_url}")

                        # Set headers dynamically
                        headers = {
                            "Authorization": f"Bearer {API_KEY}",
                            "Accept": accept_header,  # Dynamically set the Accept header based on file type
                        }
                        # Fetch the actual document
                        try:
                            document_response = requests.get(document_url, headers=headers, timeout=20)
                            document_response.raise_for_status()
                            logger.info(f"Successfully downloaded {file_extension} document for {company_number}")
                        except requests.exceptions.RequestException as e:
                            logger.error(f"Failed to download {file_extension} document for {company_number}: {e}")
                            continue

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
            sleep_time = 0.8  # Wait time between requests (to stay within rate limit)

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
        'company_number': company_number,
        'data_type': data_type
    })


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
    """
    Fetches the SIC hierarchy dynamically and structures it for rendering in the template.
    """
    sic_tree = []

    # Fetch all divisions with related groups and classes
    divisions = SicDivision.objects.prefetch_related("groups__classes").order_by("code")

    for division in divisions:
        division_data = {
            "code": division.code,
            "description": division.description,
            "groups": []
        }

        for group in division.groups.all().order_by("code"):
            group_data = {
                "code": group.code,
                "description": group.description,
                "classes": []
            }

            for sic_class in group.classes.all().order_by("code"):
                group_data["classes"].append({
                    "code": sic_class.code,
                    "description": sic_class.description
                })

            division_data["groups"].append(group_data)

        sic_tree.append(division_data)

    return render(request, "company_data/available_sic_codes.html", {
        "sic_tree": sic_tree
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


def filter_company_render(request):
    """
    Render the initial financial statement filter page without loading any companies.
    """
    # Load only the filter options (SIC Division, Group, Class)
    divisions = SicDivision.objects.all()
    groups = SicGroup.objects.all()
    classes = SicClass.objects.all()

    # Render the template with filter options
    return render(
            request,
            'company_data/financial_statements_list.html',
            {'divisions': divisions, 'groups': groups, 'classes': classes}
        )


def financial_statements_list(request): 
    """
    Handle filtering and fetching financial statements based on user input.
    """
    # Get filter parameters from GET request
    turnover_revenue_min = request.GET.get("turnover_revenue_min")
    turnover_revenue_max = request.GET.get("turnover_revenue_max")
    operating_profit_loss_min = request.GET.get("operating_profit_loss_min")
    operating_profit_loss_max = request.GET.get("operating_profit_loss_max")
    division_id = request.GET.get("division")
    group_id = request.GET.get("group")
    class_id = request.GET.get("class")

    # Check if any filter parameter is present
    if any([
        turnover_revenue_min,
        turnover_revenue_max,
        operating_profit_loss_min,
        operating_profit_loss_max,
        division_id,
        group_id,
        class_id
    ]):
        # Start with all financial statements
        financial_statements = FinancialStatement.objects.all()

        # Apply filters
        if turnover_revenue_min:
            turnover_revenue_min = float(turnover_revenue_min) * 1_000_000
            financial_statements = financial_statements.filter(turnover_revenue__gte=turnover_revenue_min)
        if turnover_revenue_max:
            turnover_revenue_max = float(turnover_revenue_max) * 1_000_000
            financial_statements = financial_statements.filter(turnover_revenue__lte=turnover_revenue_max)
        if operating_profit_loss_min:
            operating_profit_loss_min = float(operating_profit_loss_min) * 1_000_000
            financial_statements = financial_statements.filter(operating_profit_loss__gte=operating_profit_loss_min)
        if operating_profit_loss_max:
            operating_profit_loss_max = float(operating_profit_loss_max) * 1_000_000
            financial_statements = financial_statements.filter(operating_profit_loss__lte=operating_profit_loss_max)
        if class_id:
            financial_statements = financial_statements.filter(sic_code_1__startswith=class_id)
        elif group_id:
            financial_statements = financial_statements.filter(sic_code_1__startswith=group_id)
        elif division_id:
            financial_statements = financial_statements.filter(sic_code_1__startswith=division_id)
    else:
        # Return an empty queryset if no filters are selected
        financial_statements = FinancialStatement.objects.none()

    # Ensure stable pagination by applying ordering
    financial_statements = financial_statements.order_by("company_name") 

    # Paginate results
    paginator = Paginator(financial_statements, 25)  # 25 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Return the filtered results
    return render(
        request,
        'company_data/financial_statements_list.html',
        {
            'financial_statements': page_obj,
            'divisions': SicDivision.objects.all(),
            'groups': SicGroup.objects.all(),
            'classes': SicClass.objects.all(),
            'num_statements': financial_statements.count(),
        }
    )


def get_groups(request):
    division_code = request.GET.get("division_code")
    groups = SicGroup.objects.filter(division__code=division_code) if division_code else SicGroup.objects.all()
    data = [{"code": group.code, "description": group.description} for group in groups]
    return JsonResponse(data, safe=False)

def get_classes(request):
    group_code = request.GET.get("group_code")
    classes = SicClass.objects.filter(group__code=group_code) if group_code else SicClass.objects.all()
    data = [{"code": cls.code, "description": cls.description} for cls in classes]
    return JsonResponse(data, safe=False)

def model_field_counts(request):
    """
    View to display all models, their fields, and non-null counts for each field.
    """

    cache_key = "model_field_counts"

    # Handle refresh logic
    if request.GET.get("refresh") == "true":
        cache.delete(cache_key)
        return JsonResponse({"status": "success", "message": "Cache cleared and data refreshed."})

    # Fetch from cache
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, "company_data/model_field_counts.html", {"models_data": cached_data})

    # If no cache exists, calculate data
    all_models_data = []

    for model in apps.get_models():
        model_name = model._meta.verbose_name.title()
        model_fields = model._meta.get_fields()

        if model._meta.proxy or not model._meta.managed:
            continue

        field_data = []
        for field in model_fields:
            if hasattr(field, "attname"):
                field_name = field.name
                non_null_count = model.objects.exclude(**{f"{field_name}__isnull": True}).count()
                field_data.append({"field_name": field_name, "non_null_count": non_null_count})

        all_models_data.append({
            "model_name": model_name,
            "fields": field_data,
            "total_records": model.objects.count(),
        })

    # Cache data for 24 hours
    cache.set(cache_key, all_models_data, timeout=86400)

    return render(request, "company_data/model_field_counts.html", {"models_data": all_models_data})


@csrf_exempt
def add_to_interest(request):
    if request.method == "POST":
        try:
            # Parse JSON request body
            body = json.loads(request.body)
            company_number = body.get("company_number")

            if not company_number:
                return JsonResponse({"status": "error", "message": "Company number is required"}, status=400)

            # Fetch the company details
            company = Company.objects.filter(company_number=company_number).first()

            if not company:
                return JsonResponse({"status": "error", "message": "Company not found"}, status=404)

            # Add the company to CompanyOfInterest
            CompanyOfInterest.objects.get_or_create(
                company_number=company.company_number,
                defaults={
                    "company_name": company.company_name,
                    "sic_code_1": company.sic_code_1,
                },
            )

            return JsonResponse({"status": "success", "message": "Company added to interests successfully"})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


def company_of_interest_list(request):
    """
    View to display all rows from the CompanyOfInterest model in a Bootstrap table.
    """
    companies_of_interest = CompanyOfInterest.objects.all()
    return render(request, "company_data/company_of_interest_list.html", {"companies_of_interest": companies_of_interest})