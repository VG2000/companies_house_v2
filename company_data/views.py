import logging
import json
import os
import mimetypes
from django.db.models import Q
from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django import forms
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from company_data.models import Company, CompanyFiles
from django.shortcuts import render
from django.http import JsonResponse
from django.apps import apps
import requests
import base64
import logging
import json
import time
from company_data.forms import CompanyFilterForm
from company_data.models import (Company, 
                                 FinancialStatement, 
                                 CompanyOfInterest, 
                                 SicClass, 
                                 SicDivision, 
                                 SicGroup, 
                                 FinancialMetrics, 
                                 ITLLevel1,
                                 ITLLevel2,
                                 ITLLevel3,
                                 LocalAdministrativeUnit,
                                 Postcode,
)
from company_data.utils import parse_and_save_financial_statement
from company_data.file_parser import parse_zip_files
from company_data.companies_house_company_parser import process_company_data, fetch_and_update_company_data
from company_data.test_parser import test_process_statements, test_fetch_and_update_company_data, fetch_and_parse_all_statements

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

@csrf_exempt  # Allows AJAX POST request without CSRF token
def test_fetch_and_parse_first_statement_view(request):
    if request.method == "POST":
        try:
            fetch_and_parse_all_statements()  # Calls the function to process statements
            return JsonResponse({"status": "success", "message": "Statements processed successfully!"})
        except Exception as e:
            logger.error(f"Error processing statements: {e}")
            return JsonResponse({"status": "error", "message": "Error processing statements."}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)

@csrf_exempt  # Allows AJAX POST request without CSRF token
def test_process_statements_view(request):
    if request.method == "POST":
        try:
            test_process_statements()  # Calls the function to process statements
            return JsonResponse({"status": "success", "message": "Statements processed successfully!"})
        except Exception as e:
            logger.error(f"Error processing statements: {e}")
            return JsonResponse({"status": "error", "message": "Error processing statements."}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)


@csrf_exempt  # Allows AJAX POST request without CSRF token
def test_fetch_and_update_company_data_view(request):
    if request.method == "POST":
        try:
            test_fetch_and_update_company_data()  # Calls the function to process statements
            return JsonResponse({"status": "success", "message": "Company model updated successfully!"})
        except Exception as e:
            logger.error(f"Error updating Ccompany model: {e}")
            return JsonResponse({"status": "error", "message": "Error updating company model."}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)

@csrf_exempt
def process_company_data_view(request):
    """
    View to trigger processing of company data.
    """
    if request.method == "POST":
        try:
            # Call the function to process the CSV data
            process_company_data()
            logger.info("Company data processing triggered via view.")
            return JsonResponse({"status": "success", "message": "Company data successfully processed!"})
        except Exception as e:
            logger.error(f"Error processing company data: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": "An error occurred while processing company data."})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


@csrf_exempt
def update_accounts_paper_filed_view(request):
    """
    View to trigger processing of company data.
    """
    if request.method == "POST":
        try:
            logger.info("🔄 Running fetch_and_update_company_data() inside the view...")
            
            # Call the function directly (no threading, runs synchronously)
            fetch_and_update_company_data()

            logger.info("✅ Update process completed.")
            return JsonResponse({"status": "success", "message": "Company data paper filed updates successfully processed!"})

        except Exception as e:
            logger.error(f"❌ Error processing company data: {e}", exc_info=True)
            return JsonResponse({"status": "error", "message": "An error occurred while updating company data."})

    return JsonResponse({"status": "error", "message": "Invalid request method."})


@csrf_exempt
def update_financial_metrics(request):
    """
    Django view to trigger the parse_zip function and update financial metrics.
    """
    if request.method == "POST":
        try:
            parse_zip_files()  # Call the function to process ZIP files
            return JsonResponse({"message": "Financial metrics updated successfully."}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method."}, status=405)
    

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

def get_itl2(request):
    """Returns ITL Level 2 options based on selected ITL Level 1"""
    itl1_code = request.GET.get("itl1_code")
    itl2_levels = ITLLevel2.objects.filter(itl1__code=itl1_code).order_by("name") if itl1_code else ITLLevel2.objects.all()
    data = [{"code": level.code, "name": level.name} for level in itl2_levels]
    return JsonResponse(data, safe=False)

def get_itl3(request):
    """Returns ITL Level 3 options based on selected ITL Level 2"""
    itl2_code = request.GET.get("itl2_code")
    itl3_levels = ITLLevel3.objects.filter(itl2__code=itl2_code).order_by("name") if itl2_code else ITLLevel3.objects.all()
    data = [{"code": level.code, "name": level.name} for level in itl3_levels]
    return JsonResponse(data, safe=False)

def get_lau(request):
    """Returns Local Administrative Units (LAU) based on selected ITL Level 3"""
    itl3_code = request.GET.get("itl3_code")
    lau_levels = LocalAdministrativeUnit.objects.filter(itl3__code=itl3_code).order_by("name") if itl3_code else LocalAdministrativeUnit.objects.all()
    data = [{"code": level.code, "name": level.name} for level in lau_levels]
    return JsonResponse(data, safe=False)

def search_postcode(request):
    query = request.GET.get("postcode", "").strip()
    error = ""
    if not query:
        error = f"No data found for postcode: {query}"

    postcode_record = Postcode.objects.filter(code=query).first()
    logger.info(f"Postcode record for {query}: {postcode_record}")
    return render(request, 'company_data/postcode_search.html', {
        'postcode_record': postcode_record,
        'error': error,
    })

def company_filter_view(request):
    logger.info("Entering company_filter_view")

    # Get total count of all companies (before applying filters)
    total_company_count = Company.objects.count()
    logger.info(f"Total company count in database: {total_company_count}")

    # Fetch SIC divisions, groups, and classes for dependent filtering
    logger.info("Fetching SIC codes from SIC models")
    divisions = SicDivision.objects.all().order_by('code')
    groups = SicGroup.objects.all().order_by('code')
    classes = SicClass.objects.all().order_by('code')

    logger.info(f"Fetched SIC Divisions: {divisions.count()}, SIC Groups: {groups.count()}, SIC Classes: {classes.count()}")

    # Fetch ITL regions for dependent filtering
    logger.info("Fetching ITL codes from ITL models")
    itl1_levels = ITLLevel1.objects.all().order_by('name')
    itl2_levels = ITLLevel2.objects.all().order_by('name')
    itl3_levels = ITLLevel3.objects.all().order_by('name')
    lau_levels = LocalAdministrativeUnit.objects.all().order_by('name')

    logger.info(f"Fetched ITL Levels - ITL1: {itl1_levels.count()}, ITL2: {itl2_levels.count()}, ITL3: {itl3_levels.count()}, LAU: {lau_levels.count()}")

    # Get selected filters from request
    selected_division = request.GET.get('division')
    selected_group = request.GET.get('group')
    selected_class = request.GET.get('class')

    selected_itl1 = request.GET.get('itl1')
    selected_itl2 = request.GET.get('itl2')
    selected_itl3 = request.GET.get('itl3')
    selected_lau = request.GET.get('lau')

    # Initialize form
    form = CompanyFilterForm(request.GET or None)

    filtered_count = 0
    filtered_companies = Company.objects.none()  # Default empty queryset
    page_obj = None

    if request.GET and form.is_valid():
        logger.info("Filters applied, validating form data")
        try:
            filters = Q()
            logger.info(f"Filter criteria - Division: {selected_division}, Group: {selected_group}, Class: {selected_class}")

            # SIC Filtering Logic
            if selected_class:
                filters &= Q(sic_code_1__startswith=selected_class)  # Match full 6 digits
            if selected_group:
                filters &= Q(sic_code_1__startswith=selected_group)  # Match first 3 digits
            if selected_division:
                filters &= Q(sic_code_1__startswith=selected_division)  # Match first 2 digits

            # ITL Filtering Logic
            if selected_lau:
                filters &= Q(reg_address_postcode__in=Postcode.objects.filter(district__code=selected_lau).values_list("code", flat=True))

            elif selected_itl3:
                filters &= Q(reg_address_postcode__in=Postcode.objects.filter(district__itl3__code=selected_itl3).values_list("code", flat=True))

            elif selected_itl2:
                filters &= Q(reg_address_postcode__in=Postcode.objects.filter(district__itl3__itl2__code=selected_itl2).values_list("code", flat=True))

            elif selected_itl1:
                filters &= Q(reg_address_postcode__in=Postcode.objects.filter(district__itl3__itl2__itl1__code=selected_itl1).values_list("code", flat=True))


            logger.info(f"Applying filters: {filters}")

            # Apply filters
            filtered_companies = Company.objects.filter(filters).order_by("company_name")
            filtered_count = filtered_companies.count()
            logger.info(f"Filtered companies count: {filtered_count}")

        except Exception as e:
            logger.error(f"Error applying filters: {e}")

    # Pagination
    paginator = Paginator(filtered_companies, 20)
    page_number = request.GET.get('page', 1)  # Default to page 1
    page_obj = paginator.get_page(page_number)

    return render(request, 'company_data/company_filter.html', {
        'form': form,
        'total_company_count': total_company_count,
        'filtered_count': filtered_count,
        'page_obj': page_obj,
        'sic_divisions': divisions,
        'sic_groups': groups,
        'sic_classes': classes,
        'selected_division': selected_division,
        'selected_group': selected_group,
        'selected_class': selected_class,
        'itl1_levels': itl1_levels,
        'itl2_levels': itl2_levels,
        'itl3_levels': itl3_levels,
        'lau_levels': lau_levels,
        'selected_itl1': selected_itl1,
        'selected_itl2': selected_itl2,
        'selected_itl3': selected_itl3,
        'selected_lau': selected_lau,
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
    selected_division = request.GET.get("division")
    selected_group = request.GET.get("group")
    selected_class = request.GET.get("class")

    filters = Q()

    # Apply revenue filters
    if turnover_revenue_min:
        turnover_revenue_min = float(turnover_revenue_min) * 1_000_000
        filters &= Q(turnover_revenue__gte=turnover_revenue_min)
    if turnover_revenue_max:
        turnover_revenue_max = float(turnover_revenue_max) * 1_000_000
        filters &= Q(turnover_revenue__lte=turnover_revenue_max)

    # Apply profit/loss filters
    if operating_profit_loss_min:
        operating_profit_loss_min = float(operating_profit_loss_min) * 1_000_000
        filters &= Q(operating_profit_loss__gte=operating_profit_loss_min)
    if operating_profit_loss_max:
        operating_profit_loss_max = float(operating_profit_loss_max) * 1_000_000
        filters &= Q(operating_profit_loss__lte=operating_profit_loss_max)

    # Apply SIC filtering hierarchy (same as company_filter_view)
    if selected_class:
        filters &= Q(sic_code_1__startswith=selected_class)  # Match full 6 digits
    elif selected_group:
        filters &= Q(sic_code_1__startswith=selected_group)  # Match first 3 digits
    elif selected_division:
        filters &= Q(sic_code_1__startswith=selected_division)  # Match first 2 digits

    # Apply filters to the queryset
    financial_statements = FinancialStatement.objects.filter(filters).order_by("company_name")

    # Pagination
    paginator = Paginator(financial_statements, 25)  # 25 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Return the filtered results
    return render(
        request,
        'company_data/financial_statements_list.html',
        {
            'page_obj': page_obj,
            'divisions': SicDivision.objects.all(),
            'groups': SicGroup.objects.all(),
            'classes': SicClass.objects.all(),
            'num_statements': financial_statements.count(),
            'selected_division': selected_division,
            'selected_group': selected_group,
            'selected_class': selected_class,
        }
    )


def new_filter_statements_render(request):
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
            'company_data/new_financial_statement_search.html',
            {'divisions': divisions, 'groups': groups, 'classes': classes}
        )


def new_financial_statements_list(request):
    """
    Handle filtering and fetching financial statements based on user input.
    """

    # Get filter parameters from GET request
    turnover_revenue_min = request.GET.get("turnover_revenue_min")
    turnover_revenue_max = request.GET.get("turnover_revenue_max")
    profit_loss_min = request.GET.get("profit_loss_min")
    profit_loss_max = request.GET.get("profit_loss_max")
    selected_division = request.GET.get("division")
    selected_group = request.GET.get("group")
    selected_class = request.GET.get("class")
    selected_locality = request.GET.get("locality")  # New Locality filter

    # Initialize filters
    filters = Q()

    # Check if any filters are applied
    filter_applied = any([
        turnover_revenue_min, turnover_revenue_max,
        profit_loss_min, profit_loss_max,
        selected_division, selected_group, selected_class, selected_locality
    ])

    # Apply filters only if at least one is provided
    if filter_applied:
        # Revenue filters
        if turnover_revenue_min:
            turnover_revenue_min = float(turnover_revenue_min) * 1_000_000
            filters &= Q(TurnoverRevenue__gte=turnover_revenue_min)
        if turnover_revenue_max:
            turnover_revenue_max = float(turnover_revenue_max) * 1_000_000
            filters &= Q(TurnoverRevenue__lte=turnover_revenue_max)

        # Profit/loss filters
        if profit_loss_min:
            profit_loss_min = float(profit_loss_min) * 1_000_000
            filters &= Q(ProfitLoss__gte=profit_loss_min)
        if profit_loss_max:
            profit_loss_max = float(profit_loss_max) * 1_000_000
            filters &= Q(ProfitLoss__lte=profit_loss_max)

        # SIC filtering hierarchy
        if selected_class:
            filters &= Q(sic_code_1__startswith=selected_class)
        elif selected_group:
            filters &= Q(sic_code_1__startswith=selected_group)
        elif selected_division:
            filters &= Q(sic_code_1__startswith=selected_division)

        # Apply locality filter
        if selected_locality:
            filters &= Q(locality__icontains=selected_locality)  # Case-insensitive match

        # Apply filters to the queryset
        financial_statements = FinancialMetrics.objects.filter(filters).order_by("company_name")
    else:
        financial_statements = FinancialMetrics.objects.none()  # Return an empty queryset if no filters

    # Pagination
    paginator = Paginator(financial_statements, 25)  # 25 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Return the filtered results
    return render(
        request,
        'company_data/new_financial_statement_search.html',
        {
            'page_obj': page_obj,
            'divisions': SicDivision.objects.all(),
            'groups': SicGroup.objects.all(),
            'classes': SicClass.objects.all(),
            'num_statements': financial_statements.count(),
            'selected_division': selected_division,
            'selected_group': selected_group,
            'selected_class': selected_class,
            'selected_locality': selected_locality,  # Pass to template
        }
    )




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