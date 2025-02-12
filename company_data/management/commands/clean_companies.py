from django.core.management.base import BaseCommand
from django.utils.timezone import datetime
from company_data.models import Company
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Delete all Company records except those with company_status='Active', accounts_account_category='FULL' or 'GROUP', and accounts_next_due_date > 01/01/2025."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Starting company data cleanup..."))

        # Define the cutoff date
        cutoff_date = datetime(2025, 1, 1).date()

        # Filter companies that should be retained
        retained_companies = Company.objects.filter(
            company_status="Active",
            accounts_account_category__in=["FULL", "GROUP"],
            accounts_next_due_date__gt=cutoff_date  # Retain only if due date is after 01/01/2025
        )

        retained_count = retained_companies.count()
        total_count = Company.objects.count()

        if retained_count == total_count:
            self.stdout.write(self.style.SUCCESS("No records to delete. All companies meet the criteria."))
            return

        # Delete all companies that don't match the criteria
        deleted_count, _ = Company.objects.exclude(
            company_status="Active",
            accounts_account_category__in=["FULL", "GROUP"],
            accounts_next_due_date__gt=cutoff_date  # Exclude companies with a valid due date
        ).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted_count} companies. Retained {retained_count} companies."
        ))

        logger.info(f"Cleanup complete: Deleted {deleted_count} companies, Retained {retained_count} companies.")
