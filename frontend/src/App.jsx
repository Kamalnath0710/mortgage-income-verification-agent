// frontend/src/App.jsx
import React, { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [activeRole, setActiveRole] = useState("INTERNAL"); // "INTERNAL" | "BUSINESS"
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [internalJobs, setInternalJobs] = useState([]);
  const [businessJobs, setBusinessJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [reviewerName, setReviewerName] = useState("Sr. Underwriter (Internal QA)");
  const [reviewerNotes, setReviewerNotes] = useState("");

  const fetchAllQueues = async () => {
    try {
      const [intRes, bizRes] = await Promise.all([
        fetch(`${API_BASE}/internal/jobs`),
        fetch(`${API_BASE}/business/jobs`),
      ]);
      const intData = await intRes.json();
      const bizData = await bizRes.json();
      setInternalJobs(intData);
      setBusinessJobs(bizData);
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    }
  };

  useEffect(() => {
    fetchAllQueues();
  }, [activeRole]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!files.length) return alert("Select PDFs from backend/sample_docs first!");
    setLoading(true);
    const formData = new FormData();
    Array.from(files).forEach((f) => formData.append("files", f));

    try {
      const res = await fetch(`${API_BASE}/jobs/upload?state_code=CA`, {
        method: "POST",
        body: formData,
      });
      const newJob = await res.json();
      await fetchAllQueues();
      setSelectedJob(newJob);
      setReviewerNotes(newJob.reviewer_notes || "");
    } catch (err) {
      alert("Error running agent: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDocFieldChange = (idx, field, value) => {
    const updatedDocs = [...selectedJob.extracted_documents];
    updatedDocs[idx] = { ...updatedDocs[idx], [field]: value };
    setSelectedJob({ ...selectedJob, extracted_documents: updatedDocs });
  };

  const handleHITLDecision = async (action) => {
    if (!selectedJob) return;
    const payload = {
      extracted_documents: selectedJob.extracted_documents,
      mismatches: selectedJob.mismatches,
      qualifying_annual_income: Number(selectedJob.qualifying_annual_income),
      ai_executive_summary: selectedJob.ai_executive_summary,
      reviewer_notes: reviewerNotes,
      reviewed_by: reviewerName,
      action,
    };

    const res = await fetch(`${API_BASE}/internal/jobs/${selectedJob.job_id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const updated = await res.json();
    setSelectedJob(updated);
    await fetchAllQueues();
    alert(`Job ${updated.job_id} marked as ${updated.status}!`);
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 1200, margin: "0 auto", padding: 24 }}>
      {/* Top Header & Role Switcher */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "2px solid #e2e8f0", paddingBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24 }}>U.S. Mortgage Income Verification Agent</h1>
          <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 14 }}>
            Local Ollama LLM + CFPB HMDA Benchmark + Human-in-the-Loop (HITL) Gate
          </p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={() => setActiveRole("INTERNAL")}
            style={{
              padding: "10px 16px",
              fontWeight: 600,
              borderRadius: 6,
              border: "none",
              cursor: "pointer",
              background: activeRole === "INTERNAL" ? "#1e40af" : "#e2e8f0",
              color: activeRole === "INTERNAL" ? "#fff" : "#1e293b",
            }}
          >
            1. Internal Reviewer Workbench (HITL) ({internalJobs.filter((j) => j.status === "PENDING_HITL").length} Pending)
          </button>
          <button
            onClick={() => setActiveRole("BUSINESS")}
            style={{
              padding: "10px 16px",
              fontWeight: 600,
              borderRadius: 6,
              border: "none",
              cursor: "pointer",
              background: activeRole === "BUSINESS" ? "#047857" : "#e2e8f0",
              color: activeRole === "BUSINESS" ? "#fff" : "#1e293b",
            }}
          >
            2. Business User Portal ({businessJobs.length} Approved)
          </button>
        </div>
      </div>

      {/* INTERNAL REVIEWER (HITL) VIEW */}
      {activeRole === "INTERNAL" && (
        <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 24, marginTop: 24 }}>
          {/* Left Column: Upload & Queue */}
          <div>
            <form onSubmit={handleUpload} style={{ background: "#f8fafc", padding: 16, borderRadius: 8, border: "1px solid #cbd5e1" }}>
              <h3 style={{ marginTop: 0 }}>Ingest Borrower PDFs</h3>
              <input
                type="file"
                multiple
                accept=".pdf"
                onChange={(e) => setFiles(e.target.files)}
                style={{ marginBottom: 12, width: "100%" }}
              />
              <button
                type="submit"
                disabled={loading}
                style={{ width: "100%", padding: "10px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, fontWeight: 600, cursor: "pointer" }}
              >
                {loading ? "Running Ollama Extraction Agent..." : "Run Agent & Queue for HITL"}
              </button>
            </form>

            <h3 style={{ marginTop: 24 }}>Internal HITL Queue</h3>
            {internalJobs.length === 0 && <p style={{ color: "#64748b" }}>No jobs uploaded yet.</p>}
            {internalJobs.map((job) => (
              <div
                key={job.job_id}
                onClick={() => {
                  setSelectedJob(job);
                  setReviewerNotes(job.reviewer_notes || "");
                }}
                style={{
                  padding: 12,
                  marginBottom: 10,
                  borderRadius: 6,
                  cursor: "pointer",
                  border: selectedJob?.job_id === job.job_id ? "2px solid #2563eb" : "1px solid #cbd5e1",
                  background: job.status === "APPROVED" ? "#f0fdf4" : "#fffbeb",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 600 }}>
                  <span>{job.job_id}</span>
                  <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 4, background: job.status === "APPROVED" ? "#bbf7d0" : "#fde68a" }}>
                    {job.status}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#475569", marginTop: 4 }}>
                  Docs: {job.extracted_documents.length} | Flags: {job.mismatches.length}
                </div>
              </div>
            ))}
          </div>

          {/* Right Column: HITL Inspection & Override Editor */}
          <div>
            {!selectedJob ? (
              <div style={{ padding: 40, textAlign: "center", color: "#64748b", border: "1px dashed #cbd5e1", borderRadius: 8 }}>
                Select a job from the queue or upload synthetic PDFs to begin Human-in-the-Loop verification.
              </div>
            ) : (
              <div style={{ background: "#fff", padding: 20, borderRadius: 8, border: "1px solid #cbd5e1" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h2 style={{ margin: 0 }}>HITL Verification Workbench: {selectedJob.job_id}</h2>
                  <span style={{ fontWeight: 700, color: selectedJob.status === "APPROVED" ? "#047857" : "#b45309" }}>
                    Status: {selectedJob.status} (Hidden from Business UI until Approved)
                  </span>
                </div>

                {/* Extracted Document Fields Table (Editable by Internal User) */}
                <h4 style={{ marginBottom: 8 }}>1. Agent-Extracted Document Fields (Editable by Reviewer)</h4>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f1f5f9", textAlign: "left" }}>
                      <th style={{ padding: 8, border: "1px solid #cbd5e1" }}>File / Type</th>
                      <th style={{ padding: 8, border: "1px solid #cbd5e1" }}>Borrower Name</th>
                      <th style={{ padding: 8, border: "1px solid #cbd5e1" }}>Employer / Business</th>
                      <th style={{ padding: 8, border: "1px solid #cbd5e1" }}>Gross / YTD ($)</th>
                      <th style={{ padding: 8, border: "1px solid #cbd5e1" }}>W-2 Box 1 ($)</th>
                      <th style={{ padding: 8, border: "1px solid #cbd5e1" }}>Sched C Net ($)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedJob.extracted_documents.map((doc, idx) => (
                      <tr key={idx}>
                        <td style={{ padding: 8, border: "1px solid #cbd5e1" }}>
                          <strong>{doc.filename}</strong>
                          <br />
                          <span style={{ fontSize: 11, color: "#64748b" }}>{doc.doc_type}</span>
                        </td>
                        <td style={{ padding: 8, border: "1px solid #cbd5e1" }}>
                          <input
                             value={doc.borrower_name}
                            onChange={(e) => handleDocFieldChange(idx, "borrower_name", e.target.value)}
                            style={{ width: "95%" }}
                          />
                        </td>
                        <td style={{ padding: 8, border: "1px solid #cbd5e1" }}>
                          <input
                            value={doc.employer_or_business_name}
                            onChange={(e) => handleDocFieldChange(idx, "employer_or_business_name", e.target.value)}
                            style={{ width: "95%" }}
                          />
                        </td>
                        <td style={{ padding: 8, border: "1px solid #cbd5e1" }}>
                          Cur: ${doc.gross_pay_current.toLocaleString()}
                          <br />
                          YTD: ${doc.ytd_gross_pay.toLocaleString()}
                        </td>
                        <td style={{ padding: 8, border: "1px solid #cbd5e1" }}>
                          <input
                            type="number"
                            value={doc.w2_box1_wages}
                            onChange={(e) => handleDocFieldChange(idx, "w2_box1_wages", parseFloat(e.target.value) || 0)}
                            style={{ width: 90 }}
                          />
                        </td>
                        <td style={{ padding: 8, border: "1px solid #cbd5e1" }}>
                          <input
                            type="number"
                            value={doc.schedule_c_net_profit}
                            onChange={(e) => handleDocFieldChange(idx, "schedule_c_net_profit", parseFloat(e.target.value) || 0)}
                            style={{ width: 90 }}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Mismatch Flags */}
                <h4 style={{ marginBottom: 8, marginTop: 20 }}>2. Cross-Document Discrepancy Flags</h4>
                {selectedJob.mismatches.length === 0 ? (
                  <p style={{ color: "#047857", fontWeight: 600 }}>No mismatches detected across documents.</p>
                ) : (
                  selectedJob.mismatches.map((m, i) => (
                    <div key={i} style={{ padding: 10, marginBottom: 8, borderRadius: 6, background: m.severity === "HIGH" ? "#fef2f2" : "#fffbeb", border: "1px solid #fca5a5" }}>
                      <strong>[{m.severity}] {m.category}:</strong> {m.description}
                    </div>
                  ))
                )}

                {/* Qualifying Income & Summary Override */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16, marginTop: 16 }}>
                  <div>
                    <label style={{ fontWeight: 600, fontSize: 13 }}>Final Qualifying Annual Income ($):</label>
                    <input
                      type="number"
                      value={selectedJob.qualifying_annual_income}
                      onChange={(e) => setSelectedJob({ ...selectedJob, qualifying_annual_income: parseFloat(e.target.value) || 0 })}
                      style={{ width: "100%", padding: 8, marginTop: 4, fontSize: 16, fontWeight: 700, boxSizing: "border-box" }}
                    />
                  </div>
                  <div>
                    <label style={{ fontWeight: 600, fontSize: 13 }}>CFPB HMDA Benchmark Check:</label>
                    <div style={{ padding: 8, background: "#f8fafc", border: "1px solid #cbd5e1", borderRadius: 4, marginTop: 4, fontSize: 13 }}>
                      {selectedJob.hmda_benchmark.benchmark_note}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 16 }}>
                  <label style={{ fontWeight: 600, fontSize: 13 }}>AI Executive Summary (Editable before Business Release):</label>
                  <textarea
                    rows={3}
                    value={selectedJob.ai_executive_summary}
                    onChange={(e) => setSelectedJob({ ...selectedJob, ai_executive_summary: e.target.value })}
                    style={{ width: "100%", marginTop: 4, padding: 8 }}
                  />
                </div>

                <div style={{ marginTop: 12 }}>
                  <label style={{ fontWeight: 600, fontSize: 13 }}>Internal Underwriter Sign-off Notes:</label>
                  <input
                    placeholder="e.g., Verified LLC vs Inc via Secretary of State filing; approved conservative W-2 base + Sched C."
                    value={reviewerNotes}
                    onChange={(e) => setReviewerNotes(e.target.value)}
                    style={{ width: "100%", padding: 8, marginTop: 4 }}
                  />
                </div>

                <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
                  <button
                    onClick={() => handleHITLDecision("APPROVE")}
                    style={{ flex: 1, padding: 12, background: "#047857", color: "#fff", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}
                  >
                    Approve & Publish to Business User UI
                  </button>
                  <button
                    onClick={() => handleHITLDecision("REJECT")}
                    style={{ padding: "12px 20px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer" }}
                  >
                    Reject File
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* BUSINESS USER VIEW (ONLY SHOWS HITL-APPROVED RESULTS) */}
      {activeRole === "BUSINESS" && (
        <div style={{ marginTop: 24 }}>
          <div style={{ background: "#ecfdf5", padding: 16, borderRadius: 8, border: "1px solid #6ee7b7", marginBottom: 20 }}>
            <strong>Business User Portal (Loan Officer / Processor View):</strong> Only income verification packages that have passed Internal HITL Review appear below. Unverified AI extractions are strictly hidden.
          </div>

          {businessJobs.length === 0 ? (
            <div style={{ padding: 48, textAlign: "center", color: "#64748b", border: "1px dashed #cbd5e1", borderRadius: 8 }}>
              No verified loan packages have been released yet. Switch to the <strong>Internal Reviewer Workbench</strong> to approve a pending extraction.
            </div>
          ) : (
            businessJobs.map((job) => (
              <div key={job.job_id} style={{ background: "#fff", padding: 20, borderRadius: 8, border: "1px solid #cbd5e1", marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #e2e8f0", paddingBottom: 12 }}>
                  <div>
                    <h3 style={{ margin: 0 }}>Loan Verification ID: {job.job_id}</h3>
                    <span style={{ fontSize: 12, color: "#047857", fontWeight: 600 }}>
                      Verified by {job.reviewed_by} at {job.reviewed_at}
                    </span>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 12, color: "#64748b" }}>Approved Qualifying Income</div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: "#047857" }}>
                      ${job.qualifying_annual_income.toLocaleString()} / yr
                    </div>
                  </div>
                </div>

                <p style={{ marginTop: 12, lineHeight: 1.5 }}>
                  <strong>Executive Summary:</strong> {job.ai_executive_summary}
                </p>
                {job.reviewer_notes && (
                  <p style={{ background: "#f8fafc", padding: 10, borderRadius: 6, borderLeft: "4px solid #047857", fontSize: 14 }}>
                    <strong>Underwriter Reviewer Notes:</strong> {job.reviewer_notes}
                  </p>
                )}
                <p style={{ fontSize: 13, color: "#475569", marginBottom: 0 }}>
                  <strong>CFPB HMDA Context:</strong> {job.hmda_benchmark.benchmark_note}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}