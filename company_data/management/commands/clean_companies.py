from django.core.management.base import BaseCommand
from company_data.models import Company
from datetime import date
import logging

# ✅ Configure logging
logging.basicConfig(
    filename="delete_old_companies.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class Command(BaseCommand):  # ✅ Django requires this class
    help = "Deletes all Company records where returns_next_due_date is before 1st January 2025."

    def handle(self, *args, **kwargs):
        """
        Deletes all Company records where returns_next_due_date is before 1st January 2025.
        """
        cutoff_date = date(2025, 1, 1)
        companies_to_delete = Company.objects.filter(returns_next_due_date__lt=cutoff_date)

        total_deleted = companies_to_delete.count()
        logging.info(f"🚨 Found {total_deleted} companies to delete with returns_next_due_date before {cutoff_date}.")

        if total_deleted > 0:
            companies_to_delete.delete()
            logging.info(f"✅ Successfully deleted {total_deleted} old company records.")
            self.stdout.write(self.style.SUCCESS(f"✅ Deleted {total_deleted} company records before {cutoff_date}."))
        else:
            self.stdout.write(self.style.WARNING("⚠️ No records found to delete."))

