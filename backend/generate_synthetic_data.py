# backend/generate_synthetic_data.py
import os
import csv
from faker import Faker
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

fake = Faker("en_US")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_docs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_paystub_pdf(filename: str, borrower: str, employer: str, period_start: str, period_end: str, gross_pay: float, ytd_gross: float):
    path = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, "EARNINGS STATEMENT (PAY STUB)")
    c.setFont("Helvetica", 11)
    c.drawString(50, 720, f"Document Type: PAY_STUB")
    c.drawString(50, 700, f"Employer Name: {employer}")
    c.drawString(50, 680, f"Employee / Borrower Name: {borrower}")
    c.drawString(50, 660, f"Pay Period: {period_start} to {period_end}")
    c.drawString(50, 640, f"Pay Frequency: Semi-Monthly (24 pay periods/year)")
    c.drawString(50, 610, f"Current Gross Pay: ${gross_pay:,.2f}")
    c.drawString(50, 590, f"YTD Gross Earnings: ${ytd_gross:,.2f}")
    c.save()
    print(f"Created {path}")


def create_w2_pdf(filename: str, borrower: str, employer: str, tax_year: int, box1_wages: float, box2_fed_tax: float):
    path = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, f"FORM W-2 WAGE AND TAX STATEMENT ({tax_year})")
    c.setFont("Helvetica", 11)
    c.drawString(50, 720, f"Document Type: W2")
    c.drawString(50, 700, f"c. Employer's name, address, and ZIP code: {employer}")
    c.drawString(50, 680, f"e. Employee's name: {borrower}")
    c.drawString(50, 660, f"Tax Year: {tax_year}")
    c.drawString(50, 630, f"Box 1 - Wages, tips, other compensation: ${box1_wages:,.2f}")
    c.drawString(50, 610, f"Box 2 - Federal income tax withheld: ${box2_fed_tax:,.2f}")
    c.save()
    print(f"Created {path}")


def create_schedule_c_pdf(filename: str, borrower: str, business_name: str, tax_year: int, gross_receipts: float, total_expenses: float, net_profit: float):
    path = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(path, pagesize=LETTER)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, f"FORM 1040 SCHEDULE C - PROFIT OR LOSS FROM BUSINESS ({tax_year})")
    c.setFont("Helvetica", 11)
    c.drawString(50, 720, f"Document Type: SCHEDULE_C")
    c.drawString(50, 700, f"Name of Proprietor (Borrower): {borrower}")
    c.drawString(50, 680, f"Business Name: {business_name}")
    c.drawString(50, 660, f"Tax Year: {tax_year}")
    c.drawString(50, 630, f"Line 1 - Gross receipts or sales: ${gross_receipts:,.2f}")
    c.drawString(50, 610, f"Line 28 - Total expenses: ${total_expenses:,.2f}")
    c.drawString(50, 590, f"Line 31 - Net profit (or loss): ${net_profit:,.2f}")
    c.save()
    print(f"Created {path}")


def create_hmda_benchmark_csv():
    path = os.path.join(OUTPUT_DIR, "cfpb_hmda_benchmark.csv")
    rows = [
        {"state_code": "CA", "county_code": "06037", "loan_purpose": "1", "median_applicant_income_thousands": 118, "median_loan_amount": 525000, "max_dti_benchmark": 43.0},
        {"state_code": "TX", "county_code": "48201", "loan_purpose": "1", "median_applicant_income_thousands": 94, "median_loan_amount": 345000, "max_dti_benchmark": 43.0},
        {"state_code": "NY", "county_code": "36061", "loan_purpose": "1", "median_applicant_income_thousands": 142, "median_loan_amount": 680000, "max_dti_benchmark": 43.0},
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Created CFPB HMDA Benchmark CSV at {path}")


if __name__ == "__main__":
    # Scenario 1: Discrepancy Case (Great for testing HITL flags)
    create_paystub_pdf(
        filename="case1_paystub.pdf",
        borrower="Michael J. Carter",
        employer="Apex Cloud Systems Inc.",
        period_start="2025-10-01",
        period_end="2025-10-15",
        gross_pay=5000.00,       # $120,000 annualized (24 periods)
        ytd_gross=95000.00       # 19 periods * 5,000 = 95,000
    )
    create_w2_pdf(
        filename="case1_w2.pdf",
        borrower="Michael Carter",
        employer="Apex Cloud Solutions LLC",  # Intentional mismatch: LLC vs Systems Inc
        tax_year=2024,
        box1_wages=92000.00,                  # Intentional variance vs $120k annualized run-rate
        box2_fed_tax=14500.00
    )
    create_schedule_c_pdf(
        filename="case1_schedule_c.pdf",
        borrower="Michael J. Carter",
        business_name="Carter Advisory Group",
        tax_year=2024,
        gross_receipts=42000.00,
        total_expenses=14000.00,
        net_profit=28000.00
    )

    # Scenario 2: Clean Matching Case
    create_paystub_pdf(
        filename="case2_paystub.pdf",
        borrower="Sarah E. Jenkins",
        employer="NorthStar FinTech Corp",
        period_start="2025-10-01",
        period_end="2025-10-15",
        gross_pay=4500.00,       # $108,000 annualized
        ytd_gross=85500.00
    )
    create_w2_pdf(
        filename="case2_w2.pdf",
        borrower="Sarah E. Jenkins",
        employer="NorthStar FinTech Corp",
        tax_year=2024,
        box1_wages=107500.00,
        box2_fed_tax=18200.00
    )

    create_hmda_benchmark_csv()