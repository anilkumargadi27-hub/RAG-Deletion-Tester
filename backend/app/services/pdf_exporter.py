import io
import csv
import json
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from backend.app.models.synthetic import TestRun, ProbeResult

def sanitize_csv_cell(value: Any) -> str:
    """Escapes CSV formula prefixes (=, +, -, @) to prevent formula injection."""
    s = str(value) if value is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s

class ReportExporter:
    def export_json(self, db: Session, run_id: str) -> Dict[str, Any]:
        run = db.query(TestRun).filter(TestRun.id == run_id).first()
        if not run:
            raise ValueError("Test run not found.")

        probes = db.query(ProbeResult).filter(ProbeResult.run_id == run_id).order_by(ProbeResult.probe_index.asc()).all()

        return {
            "report_title": "ForgetCheck — RAG Deletion & Access-Revocation Audit Report",
            "tagline": "Check what your AI can still reveal after access changes.",
            "generated_at": datetime.utcnow().isoformat(),
            "run_metadata": {
                "run_id": run.id,
                "name": run.name,
                "status": run.status,
                "fault_mode": run.fault_mode,
                "answer_mode": run.answer_mode,
                "retrieval_mode": run.retrieval_mode,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "latency_avg_ms": run.latency_avg_ms
            },
            "findings_summary": {
                "total_scenarios": run.total_scenarios,
                "completed_scenarios": run.completed_scenarios,
                "total_probes": run.completed_probes,
                "leaked_count": run.leaked_count,
                "blocked_count": run.blocked_count,
                "authorized_success_count": run.authorized_success_count,
                "inconclusive_count": run.inconclusive_count,
                "detector_precision": run.detector_precision,
                "detector_recall": run.detector_recall,
                "detector_fpr": run.detector_fpr
            },
            "honesty_boundary": {
                "disclaimer": "This audit tests application retrieval, caching, and conversation context. It does not measure model weights or universal machine unlearning.",
                "conclusion_standard": "Report reads 'No leakage observed in these tests', never 'Guaranteed secure'."
            },
            "probes": [
                {
                    "probe_index": p.probe_index,
                    "scenario_key": p.scenario_key,
                    "query": p.query,
                    "probe_type": p.probe_type,
                    "target_principal": p.target_principal,
                    "pre_or_post": p.pre_or_post,
                    "response_text": p.response_text,
                    "detected_fact": p.detected_fact,
                    "verdict": p.verdict,
                    "evidence_span": p.evidence_span,
                    "latency_ms": p.latency_ms,
                    "storage_consulted": json.loads(p.storage_consulted_json),
                    "storage_contributed": json.loads(p.storage_contributed_json)
                }
                for p in probes
            ]
        }

    def export_csv(self, db: Session, run_id: str) -> str:
        data = self.export_json(db, run_id)
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "Probe Index", "Scenario Key", "Probe Type", "Principal",
            "Pre/Post Mutation", "Query", "Verdict", "Detected Fact",
            "Evidence Span", "Latency (ms)", "Storage Consulted", "Storage Contributed"
        ])

        for p in data["probes"]:
            writer.writerow([
                sanitize_csv_cell(p["probe_index"]),
                sanitize_csv_cell(p["scenario_key"]),
                sanitize_csv_cell(p["probe_type"]),
                sanitize_csv_cell(p["target_principal"]),
                sanitize_csv_cell(p["pre_or_post"]),
                sanitize_csv_cell(p["query"]),
                sanitize_csv_cell(p["verdict"]),
                sanitize_csv_cell(p["detected_fact"]),
                sanitize_csv_cell(p["evidence_span"]),
                sanitize_csv_cell(p["latency_ms"]),
                sanitize_csv_cell(", ".join(p["storage_consulted"])),
                sanitize_csv_cell(", ".join(p["storage_contributed"]))
            ])

        return output.getvalue()

    def export_pdf(self, db: Session, run_id: str) -> bytes:
        data = self.export_json(db, run_id)
        meta = data["run_metadata"]
        summary = data["findings_summary"]

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a")
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b")
        )
        heading2 = ParagraphStyle(
            'H2',
            parent=styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0369a1")
        )
        body = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b")
        )
        legal_style = ParagraphStyle(
            'Legal',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569")
        )

        story = []

        # Title & Subtitle
        story.append(Paragraph("ForgetCheck — RAG Deletion & Access-Revocation Audit", title_style))
        story.append(Paragraph("Check what your AI can still reveal after access changes.", subtitle_style))
        story.append(Spacer(1, 12))

        # Metadata Block
        meta_data = [
            [Paragraph("<b>Run ID:</b>", body), Paragraph(meta["run_id"], body),
             Paragraph("<b>Status:</b>", body), Paragraph(meta["status"].upper(), body)],
            [Paragraph("<b>Fault Mode:</b>", body), Paragraph(meta["fault_mode"], body),
             Paragraph("<b>Answer Mode:</b>", body), Paragraph(meta["answer_mode"], body)],
            [Paragraph("<b>Retrieval:</b>", body), Paragraph(meta["retrieval_mode"], body),
             Paragraph("<b>Avg Latency:</b>", body), Paragraph(f"{meta['latency_avg_ms']} ms", body)]
        ]
        meta_table = Table(meta_data, colWidths=[80, 180, 80, 180])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # Findings Summary Table
        story.append(Paragraph("Execution & Findings Summary", heading2))
        story.append(Spacer(1, 6))

        summary_data = [
            ["Total Scenarios", "Total Probes", "Leaked (Faults)", "Blocked (Secure)", "Authorized Success", "Inconclusive"],
            [
                str(summary["total_scenarios"]),
                str(summary["total_probes"]),
                str(summary["leaked_count"]),
                str(summary["blocked_count"]),
                str(summary["authorized_success_count"]),
                str(summary["inconclusive_count"])
            ]
        ]
        summary_table = Table(summary_data, colWidths=[88, 88, 88, 88, 100, 88])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284c7")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#f0f9ff")),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#bae6fd"))
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # Probes Table
        story.append(Paragraph("Probe Execution & Leak Detection Evidence", heading2))
        story.append(Spacer(1, 6))

        probe_headers = ["#", "Type", "Principal", "Query", "Verdict", "Evidence Span"]
        probe_rows = [probe_headers]
        for p in data["probes"][:35]: # Display top 35 probes for readable PDF
            v_color = colors.HexColor("#dc2626") if p["verdict"] == "leaked" else colors.HexColor("#16a34a")
            verdict_p = Paragraph(f"<b>{p['verdict'].upper()}</b>", ParagraphStyle('V', parent=body, textColor=v_color))
            q_p = Paragraph(p["query"][:65] + ("..." if len(p["query"]) > 65 else ""), body)
            ev_p = Paragraph((p["evidence_span"] or "-")[:50], body)
            probe_rows.append([
                str(p["probe_index"]),
                p["probe_type"],
                p["target_principal"],
                q_p,
                verdict_p,
                ev_p
            ])

        probe_table = Table(probe_rows, colWidths=[20, 70, 80, 180, 60, 130])
        probe_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#334155")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(probe_table)
        story.append(Spacer(1, 14))

        # Honest Product Boundary & Limitations Statement
        story.append(Paragraph("Product Boundaries & Compliance Limitations", heading2))
        story.append(Spacer(1, 4))
        boundary_text = (
            "<b>Important Boundary Notice:</b> This audit measures application-level retrieval filters, vector tombstone revalidation, "
            "database-backed answer cache invalidation, and session conversation memory pruning. "
            "It does not evaluate model weight modifications or universal machine unlearning. "
            "Information previously displayed to end-users prior to deletion cannot be revoked client-side. "
            "Report findings indicate 'No leakage observed in these tests', never 'Guaranteed secure'."
        )
        story.append(Paragraph(boundary_text, legal_style))

        doc.build(story)
        return buffer.getvalue()

report_exporter = ReportExporter()
