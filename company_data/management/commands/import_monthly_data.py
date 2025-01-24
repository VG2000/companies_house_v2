import os
import zipfile
import shutil
import logging
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from company_data.models import CompanyFiles

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Command(BaseCommand):
    help = 'Import monthly file from a zip archive'

    def add_arguments(self, parser):
        parser.add_argument('zip_file', type=str, help='The path to the zip file')

    def handle(self, *args, **kwargs):
        zip_file_path = kwargs['zip_file']

        # Check if the file exists
        if not os.path.exists(zip_file_path):
            self.stdout.write(self.style.ERROR(f'File "{zip_file_path}" does not exist'))
            logger.error(f'File "{zip_file_path}" does not exist')
            return

        # Define the media directory for HTML files
        media_dir = Path(settings.MEDIA_ROOT) / "html_files"
        media_dir.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist

        # Variables for batch processing and record collection
        batch_size = 10000
        records = []
        processed_files = 0

        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    file_name = file_info.filename
                    if file_name.endswith('.html'):  # Only process HTML files
                        try:
                            # Ensure directory structure in the target location
                            target_file_path = media_dir / file_name
                            target_file_path.parent.mkdir(parents=True, exist_ok=True)

                            # Extract the file to the media directory
                            with zip_ref.open(file_name) as source, open(target_file_path, 'wb') as target:
                                shutil.copyfileobj(source, target)

                            # Generate the file URL
                            file_url = f"{settings.MEDIA_URL}html_files/{file_name}"

                            # Extract metadata from the file name
                            parts = file_name.split('_')
                            process_number = '_'.join(parts[:2])
                            company_number = parts[2]
                            balance_sheet_date_str = parts[3].split('.')[0]
                            balance_sheet_date = datetime.strptime(balance_sheet_date_str, '%Y%m%d').date()
                            file_type = file_name.split('.')[-1]

                            # Append record to the batch
                            records.append(CompanyFiles(
                                file_url=file_url,
                                process_number=process_number,
                                company_number=company_number,
                                balance_sheet_date=balance_sheet_date,
                                file_type=file_type
                            ))
                            processed_files += 1

                            # Bulk insert records when batch size is reached
                            if len(records) >= batch_size:
                                CompanyFiles.objects.bulk_create(records)
                                logger.info(f'Inserted {len(records)} records to the database')
                                records = []  # Reset the batch
                        except Exception as e:
                            logger.error(f'Failed to process file "{file_name}": {e}')

            # Insert any remaining records in the batch
            if records:
                CompanyFiles.objects.bulk_create(records)
                logger.info(f'Inserted {len(records)} remaining records to the database')

            self.stdout.write(self.style.SUCCESS(f'Successfully processed {processed_files} HTML files from {zip_file_path}'))
            logger.info(f'Successfully processed {processed_files} HTML files from {zip_file_path}')
        except zipfile.BadZipFile:
            self.stdout.write(self.style.ERROR(f'Error: "{zip_file_path}" is not a valid zip file'))
            logger.error(f'Error: "{zip_file_path}" is not a valid zip file')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An unexpected error occurred: {e}'))
            logger.error(f'An unexpected error occurred: {e}')
