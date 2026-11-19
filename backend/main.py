# backend/main.py
import os
import uuid
import shutil
from datetime import datetime
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import VerificationJob, HITLApprovalRequest, ExtractedDocument
from agent import (
    extract_text_from_pdf,
    extract_document_fields_agent,
    cross_check_documents_agent,
    benchmark_with_hmda,
)

app = FastAPI(title="U.S. Mortgage Income Verification Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory store (replace with SQLite/PostgreSQL in production)
JOBS_DB: dict[str, VerificationJob] = {}


@app.post("/api/jobs/upload", response_model=VerificationJob)
async def upload_and_verify_documents(files: List[UploadFile] = File(...), state_code: str = "CA"):
    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF file is required.")

    job_id = f"LOAN-{str(uuid.uuid4())[:8].upper()}"
    extracted_docs: List[ExtractedDocument] = []

    for file in files:
        dest_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        raw_text = extract_text_from_pdf(dest_path)
        doc_result = extract_document_fields_agent(file.filename, raw_text)
        extracted_docs.append(doc_result)

    mismatches, qualifying_income, summary = cross_check_documents_agent(extracted_docs)
    hmda_result = benchmark_with_hmda(qualifying_income, state_code=state_code)

    job = VerificationJob(
        job_id=job_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        status="PENDING_HITL",  # Locked until Internal Reviewer approves!
        extracted_documents=extracted_docs,
        mismatches=mismatches,
        qualifying_annual_income=qualifying_income,
        ai_executive_summary=summary,
        hmda_benchmark=hmda_result,
    )
    JOBS_DB[job_id] = job
    return job


@app.get("/api/internal/jobs", response_model=List[VerificationJob])
def list_internal_hitl_jobs():
    """Returns ALL jobs (including PENDING_HITL) for the Internal Underwriter Reviewer."""
    return list(JOBS_DB.values())


@app.post("/api/internal/jobs/{job_id}/review", response_model=VerificationJob)
def submit_hitl_review(job_id: str, payload: HITLApprovalRequest):
    """Internal user edits extracted fields, resolves flags, and approves/rejects the result."""
    if job_id not in JOBS_DB:
        raise HTTPException(status_code=404, detail="Job not found")

    job = JOBS_DB[job_id]
    job.extracted_documents = payload.extracted_documents
    job.mismatches = payload.mismatches
    job.qualifying_annual_income = payload.qualifying_annual_income
    job.ai_executive_summary = payload.ai_executive_summary
    job.reviewer_notes = payload.reviewer_notes
    job.reviewed_by = payload.reviewed_by
    job.reviewed_at = datetime.utcnow().isoformat() + "Z"
    job.status = "APPROVED" if payload.action == "APPROVE" else "REJECTED"
    job.hmda_benchmark = benchmark_with_hmda(
        payload.qualifying_annual_income, state_code=job.hmda_benchmark.state_code
    )

    JOBS_DB[job_id] = job
    return job


@app.get("/api/business/jobs", response_model=List[VerificationJob])
def list_business_approved_jobs():
    """STRICT GATE: Returns ONLY jobs where the Internal User has completed HITL verification."""
    return [job for job in JOBS_DB.values() if job.status == "APPROVED"]