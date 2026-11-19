# backend/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ExtractedDocument(BaseModel):
    filename: str
    doc_type: Literal["PAY_STUB", "W2", "SCHEDULE_C", "UNKNOWN"] = Field(
        description="Classified type of mortgage income document"
    )
    borrower_name: str = Field(default="", description="Full name of employee or proprietor")
    employer_or_business_name: str = Field(default="", description="Employer name on W2/Paystub or Business Name on Schedule C")
    tax_year_or_period: str = Field(default="", description="Pay period dates or W2/Tax year")
    gross_pay_current: float = Field(default=0.0, description="Current period gross pay if Pay Stub, else 0")
    ytd_gross_pay: float = Field(default=0.0, description="YTD gross earnings if Pay Stub, else 0")
    w2_box1_wages: float = Field(default=0.0, description="Box 1 wages if W-2, else 0")
    schedule_c_net_profit: float = Field(default=0.0, description="Line 31 Net profit if Schedule C, else 0")


class MismatchFlag(BaseModel):
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    category: str
    description: str
    documents_involved: List[str]


class HMDABenchmarkResult(BaseModel):
    state_code: str
    median_tract_income: float
    calculated_qualifying_income: float
    income_to_median_ratio: float
    benchmark_note: str


class VerificationJob(BaseModel):
    job_id: str
    created_at: str
    status: Literal["PENDING_HITL", "APPROVED", "REJECTED"]
    extracted_documents: List[ExtractedDocument]
    mismatches: List[MismatchFlag]
    qualifying_annual_income: float
    ai_executive_summary: str
    hmda_benchmark: HMDABenchmarkResult
    reviewer_notes: Optional[str] = ""
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None


class HITLApprovalRequest(BaseModel):
    extracted_documents: List[ExtractedDocument]
    mismatches: List[MismatchFlag]
    qualifying_annual_income: float
    ai_executive_summary: str
    reviewer_notes: str
    reviewed_by: str
    action: Literal["APPROVE", "REJECT"]