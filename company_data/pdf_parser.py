'pip install pymupdf pdfplumber'
''
import fitz  # PyMuPDF
import pdfplumber
import re
import os
import logging
import csv
import pytesseract
import pandas as pd
from pdf2image import convert_from_path  # Converts PDF pages to images

logger = logging.getLogger(__name__)


def detect_text_in_pdf(pdf_path):
    """Checks if a PDF contains selectable text or if it is an image-based PDF."""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text("text").strip()
                if text:
                    return True  # ✅ The PDF contains selectable text
        return False  # ❌ No selectable text found (likely an image-based PDF)
    except Exception as e:
        logger.error(f"❌ Error opening PDF: {e}")
        return False

def extract_text_from_pdf(pdf_path="pdf_parser_test_pdfs", output_filename="extracted_text.txt"):
    """
    Extracts text from a PDF file using PyMuPDF.
    If the PDF is image-based, uses OCR (Tesseract) to extract text.
    """
    text = ""
    pdf_path = os.path.abspath(pdf_path)
    file = "AAMP_Global.pdf"
    full_pdf_path = os.path.join(pdf_path, file)

    # Check if the PDF file exists
    if not os.path.exists(full_pdf_path):
        logger.error(f"🚨 Error: The PDF file {full_pdf_path} does not exist.")
        return None

    # Check if PDF contains selectable text
    if detect_text_in_pdf(full_pdf_path):
        logger.info("✅ Selectable text detected. Extracting normally with PyMuPDF...")
        try:
            with fitz.open(full_pdf_path) as doc:
                for page in doc:
                    text += page.get_text("text") + "\n"
        except Exception as e:
            logger.error(f"❌ Error reading PDF with PyMuPDF: {e}")
            return None
    else:
        logger.warning("⚠️ No selectable text found. Running OCR on the PDF...")
        images = convert_from_path(full_pdf_path)  # Convert PDF to images
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"

    if not text.strip():
        logger.warning("⚠️ No text extracted from the PDF.")
        return None

    # Save extracted text to file
    output_path = os.path.join(pdf_path, output_filename)
    with open(output_path, "w", encoding="utf-8") as text_file:
        text_file.write(text)

    logger.info(f"✅ Extracted text saved to {output_path}")
    return output_path


def extract_tables_from_pdf(pdf_path="pdf_parser_test_pdfs", output_filename="extracted_tables.csv"):
    """
    Extracts tables from a PDF file using pdfplumber.
    If tables are not found, tries OCR and Pandas to detect tables from images.

    Args:
        pdf_path (str): Directory where the PDF file is located.
        output_filename (str): Name of the CSV file to save extracted tables.

    Returns:
        str: Full path of the saved CSV file, or None if extraction fails.
    """
    extracted_data = []
    pdf_path = os.path.abspath(pdf_path)
    file = "AAMP_Global.pdf"
    full_pdf_path = os.path.join(pdf_path, file)

    # Check if the PDF file exists
    if not os.path.exists(full_pdf_path):
        logger.error(f"🚨 Error: The PDF file {full_pdf_path} does not exist.")
        return None

    try:
        with pdfplumber.open(full_pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_table()
                if tables:
                    extracted_data.extend(tables)

        if not extracted_data:
            logger.warning("⚠️ No tables found with pdfplumber. Trying OCR-based table extraction...")
            images = convert_from_path(full_pdf_path)  # Convert PDF pages to images
            for img in images:
                ocr_text = pytesseract.image_to_string(img, config="--psm 6")  # OCR table mode
                lines = ocr_text.split("\n")
                table_data = [line.split() for line in lines if line.strip()]
                extracted_data.extend(table_data)

        if not extracted_data:
            logger.warning("⚠️ No tables extracted from the PDF.")
            return None

        # Define output CSV file path
        output_path = os.path.join(pdf_path, output_filename)

        # Save extracted tables to a CSV file
        df = pd.DataFrame(extracted_data)
        df.to_csv(output_path, index=False, encoding="utf-8")

        logger.info(f"✅ Extracted tables saved to {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Error reading PDF with pdfplumber: {e}")
        return None



def parse_financial_metrics(text):
    """Parses financial metrics from extracted text using regex."""
    metrics = {
        "Turnover": None,
        "Cost of Sales": None,
        "Gross Profit": None,
        "Operating Profit": None,
        "Interest Receivable": None,
        "Interest Payable": None,
        "Profit Before Tax": None,
        "Tax on Profit": None,
        "Profit for the Year": None,
        "Total Comprehensive Income": None,
    }

    # Define regex patterns for extracting financial numbers
    for metric in metrics.keys():
        pattern = rf"{metric}.*?([\d,]+)\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics[metric] = int(match.group(1).replace(",", ""))  # Convert to integer

    return metrics

def process_pdf(pdf_path):
    """Processes a PDF file to extract financial metrics."""
    print(f"Processing {pdf_path}...")

    # Extract text and tables
    text = extract_text_from_pdf(pdf_path)
    tables = extract_tables_from_pdf(pdf_path)

    # Parse metrics from text
    metrics = parse_financial_metrics(text)

    # If metrics are missing, check tables
    if any(value is None for value in metrics.values()) and tables:
        for row in tables:
            for metric in metrics.keys():
                if metric.lower() in row[0].lower():  # Match metric name
                    try:
                        metrics[metric] = int(row[1].replace(",", ""))
                    except (IndexError, ValueError):
                        pass

    print("Extracted Financial Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value if value is not None else 'N/A'}")

    return metrics

# Example usage
# pdf_path = "financial_report.pdf"  # Replace with your actual PDF file path
# process_pdf(pdf_path)
extract_tables_from_pdf()