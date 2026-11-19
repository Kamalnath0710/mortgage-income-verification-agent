# backend/agent.py
import os
import re
import csv
import json
import requests
from typing import List, Tuple
from pypdf import PdfReader
from schemas import ExtractedDocument, MismatchFlag, HMDABenchmarkResult

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def call_ollama_json(system_prompt: str, user_prompt: str) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "format": "json",
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.0,
            "num_ctx": 2048,
            "num_predict": 350,
        },
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
        parsed = json.loads(content)
        print(f"[Ollama Success] {parsed}")
        return parsed
    except Exception as e:
        print(f"[Ollama Error] {type(e).__name__}: {e}")
        return {}


def extract_document_fields_agent(filename: str, raw_text: str) -> ExtractedDocument:
    system_prompt = """You are a U.S. Mortgage Underwriting Document Extraction Agent.
Extract the exact fields from the provided document text and return ONLY valid JSON matching this schema:
{
  "doc_type": "PAY_STUB" | "W2" | "SCHEDULE_C" | "UNKNOWN",
  "borrower_name": "string",
  "employer_or_business_name": "string",
  "tax_year_or_period": "string",
  "gross_pay_current": float,
  "ytd_gross_pay": float,
  "w2_box1_wages": float,
  "schedule_c_net_profit": float
}
Convert all currency strings (e.g., '$95,000.00') to plain floats (95000.0). Use 0.0 for fields not applicable to the document type."""

    data = call_ollama_json(system_prompt, f"Filename: {filename}\n\nDocument Text:\n{raw_text}")

    doc_type = data.get("doc_type", "UNKNOWN")
    return ExtractedDocument(
        filename=filename,
        doc_type=doc_type,
        borrower_name=data.get("borrower_name", "Unknown"),
        employer_or_business_name=data.get("employer_or_business_name", "Unknown"),
        tax_year_or_period=data.get("tax_year_or_period", "Unknown"),
        gross_pay_current=float(data.get("gross_pay_current", 0.0) or 0.0) if doc_type == "PAY_STUB" else 0.0,
        ytd_gross_pay=float(data.get("ytd_gross_pay", 0.0) or 0.0) if doc_type == "PAY_STUB" else 0.0,
        w2_box1_wages=float(data.get("w2_box1_wages", 0.0) or 0.0) if doc_type == "W2" else 0.0,
        schedule_c_net_profit=float(data.get("schedule_c_net_profit", 0.0) or 0.0) if doc_type == "SCHEDULE_C" else 0.0,
    )


def cross_check_documents_agent(docs: List[ExtractedDocument]) -> Tuple[List[MismatchFlag], float, str]:
    mismatches: List[MismatchFlag] = []

    # 1. Borrower Name Cross-Check
    names = {d.borrower_name.strip() for d in docs if d.borrower_name}
    if len(names) > 1:
        mismatches.append(
            MismatchFlag(
                severity="MEDIUM",
                category="Borrower Name Variation",
                description=f"Borrower name differs across documents: {', '.join(names)}. Verify middle initial/alias via Letter of Explanation (LOE).",
                documents_involved=[d.filename for d in docs],
            )
        )

    # 2. Employer Name Cross-Check (Pay Stub vs W-2)
    emp_docs = [d for d in docs if d.doc_type in ("PAY_STUB", "W2")]
    employers = {d.employer_or_business_name.strip() for d in emp_docs if d.employer_or_business_name}
    if len(employers) > 1:
        mismatches.append(
            MismatchFlag(
                severity="HIGH",
                category="Employer Entity Mismatch",
                description=f"Employer name mismatch between Pay Stub and W-2: {', '.join(employers)}.",
                documents_involved=[d.filename for d in emp_docs],
            )
        )

    # 3. Income Calculation & Pay Stub vs W-2 Variance Check
    paystubs = [d for d in docs if d.doc_type == "PAY_STUB"]
    w2s = [d for d in docs if d.doc_type == "W2"]
    sched_cs = [d for d in docs if d.doc_type == "SCHEDULE_C"]

    base_annual_income = 0.0
    if paystubs and w2s:
        ps = paystubs[0]
        w2 = w2s[0]
        annualized_paystub = ps.gross_pay_current * 24.0  # Semi-monthly default
        variance_pct = abs(annualized_paystub - w2.w2_box1_wages) / max(w2.w2_box1_wages, 1.0) * 100.0
        if variance_pct > 10.0:
            mismatches.append(
                MismatchFlag(
                    severity="HIGH",
                    category="Annualized Base vs. W-2 Box 1 Variance",
                    description=(
                        f"Annualized Pay Stub gross (${annualized_paystub:,.2f}) differs from W-2 Box 1 "
                        f"(${w2.w2_box1_wages:,.2f}) by {variance_pct:.1f}%. Conservative underwriting uses lower verified figure."
                    ),
                    documents_involved=[ps.filename, w2.filename],
                )
            )
        # Fannie Mae conservative lower-of rule when unverified raise
        base_annual_income = min(annualized_paystub, w2.w2_box1_wages)
    elif w2s:
        base_annual_income = w2s[0].w2_box1_wages
    elif paystubs:
        base_annual_income = paystubs[0].gross_pay_current * 24.0

    sched_c_income = sum(d.schedule_c_net_profit for d in sched_cs)
    qualifying_annual_income = base_annual_income + sched_c_income

    # 4. Ask Ollama Agent for Executive Underwriting Summary
    summary_prompt = f"""You are a Senior Mortgage Underwriter AI Agent.
Summarize the income verification findings in 3 concise sentences for the underwriting file.
Extracted Documents: {json.dumps([d.model_dump() for d in docs])}
Flagged Mismatches: {json.dumps([m.model_dump() for m in mismatches])}
Calculated Qualifying Annual Income: ${qualifying_annual_income:,.2f}
Return JSON: {{"executive_summary": "string"}}"""

    llm_summary_resp = call_ollama_json(
        "Return JSON with key 'executive_summary'.", summary_prompt
    )
    summary_text = llm_summary_resp.get(
        "executive_summary",
        f"Processed {len(docs)} income documents with {len(mismatches)} flagged discrepancies. "
        f"Recommended qualifying annual income is ${qualifying_annual_income:,.2f} pending human underwriter review."
    )

    return mismatches, qualifying_annual_income, summary_text


def benchmark_with_hmda(qualifying_income: float, state_code: str = "CA") -> HMDABenchmarkResult:
    csv_path = os.path.join(os.path.dirname(__file__), "sample_docs", "cfpb_hmda_benchmark.csv")
    median_income = 110000.0
    if os.path.exists(csv_path):
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["state_code"] == state_code:
                    median_income = float(row["median_applicant_income_thousands"]) * 1000.0
                    break

    ratio = round(qualifying_income / median_income, 2) if median_income else 1.0
    note = (
        f"Borrower qualifying income (${qualifying_income:,.2f}) is {ratio}x the CFPB HMDA median applicant "
        f"income (${median_income:,.2f}) for {state_code}."
    )
    return HMDABenchmarkResult(
        state_code=state_code,
        median_tract_income=median_income,
        calculated_qualifying_income=qualifying_income,
        income_to_median_ratio=ratio,
        benchmark_note=note,
    )