import zipfile
import mimetypes
import os
from collections import defaultdict
from pathlib import Path
from lxml import etree
import logging
import base64
import requests
import time
import zipfile
import json
import re
from decimal import Decimal, InvalidOperation
from django.db import transaction, IntegrityError
from company_data.models import FinancialMetrics 

# Configure logging
logging.basicConfig(
    filename="zip_parser.log",  # Log file name
    level=logging.INFO,  # Log level (INFO, DEBUG, ERROR, etc.)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)


BASE_DIR = Path(__file__).resolve().parent
API_KEY = "17c5f21f-c601-45af-825d-b7b8cafe95b2"
BASE_URL = "https://api.company-information.service.gov.uk"
AUTH_HEADER = f"Basic {base64.b64encode(f'{API_KEY}:'.encode('utf-8')).decode('utf-8')}"
HEADERS = {"Authorization": AUTH_HEADER}