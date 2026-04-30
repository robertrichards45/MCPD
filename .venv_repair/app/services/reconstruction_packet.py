import os
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def build_reconstruction_packet_pdf(
    out_path,
    case_row,
    vehicles,
    measurements,
    attachments,
    diagram_path=None,
):
    """
    Minimal "packet" generator.
    - case_row: ReconstructionCase
    - vehicles/measurements/attachments: lists of model rows
    - diagram_path: optional filesystem path to PNG/JPG
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    c = canvas.Canvas(out_path, pagesize=letter)
    w, h = letter

    def header(title):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(0.75 * inch, h - 0.9 * inch, title)
        c.setFont("Helvetica", 10)
        c.drawRightString(w - 0.75 * inch, h - 0.9 * inch, _utcnow_naive().strftime("%Y-%m-%d %H:%MZ"))
        c.line(0.75 * inch, h - 0.95 * inch, w - 0.75 * inch, h - 0.95 * inch)

    def kv(y, k, v):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.75 * inch, y, k)
        c.setFont("Helvetica", 11)
        c.drawString(2.2 * inch, y, v or "")

    header("Accident Reconstruction Packet")
    y = h - 1.3 * inch
    kv(y, "Case", f"#{case_row.id}  {case_row.title}")
    y -= 0.25 * inch
    kv(y, "Date", case_row.incident_date or "")
    y -= 0.25 * inch
    kv(y, "Location", case_row.location or "")

    y -= 0.4 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, y, "Vehicles")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    if vehicles:
        for v in vehicles[:18]:
            line = f"- {v.unit or ''} {v.make_model or ''} {('('+v.direction+')') if v.direction else ''}".strip()
            c.drawString(0.85 * inch, y, line[:120])
            y -= 0.18 * inch
            if y < 1.2 * inch:
                c.showPage()
                header("Accident Reconstruction Packet (cont.)")
                y = h - 1.3 * inch
    else:
        c.drawString(0.85 * inch, y, "- (none)")
        y -= 0.18 * inch

    y -= 0.2 * inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75 * inch, y, "Measurements")
    y -= 0.22 * inch
    c.setFont("Helvetica", 10)
    if measurements:
        for m in measurements[:24]:
            val = (m.value or "").strip()
            units = (m.units or "").strip()
            mid = f"{val} {units}".strip()
            line = f"- {m.label}: {mid}".strip()
            c.drawString(0.85 * inch, y, line[:120])
            y -= 0.18 * inch
            if y < 1.2 * inch:
                c.showPage()
                header("Accident Reconstruction Packet (cont.)")
                y = h - 1.3 * inch
    else:
        c.drawString(0.85 * inch, y, "- (none)")
        y -= 0.18 * inch

    # Diagram page
    c.showPage()
    header("Scene Diagram")
    if diagram_path and os.path.exists(diagram_path):
        # Fit into page margins.
        x0 = 0.75 * inch
        y0 = 1.0 * inch
        max_w = w - 1.5 * inch
        max_h = h - 2.0 * inch
        try:
            c.drawImage(diagram_path, x0, y0, width=max_w, height=max_h, preserveAspectRatio=True, anchor="c")
        except Exception:
            c.setFont("Helvetica", 11)
            c.drawString(0.75 * inch, h - 1.3 * inch, "Diagram image could not be embedded. See attachments.")
    else:
        c.setFont("Helvetica", 11)
        c.drawString(0.75 * inch, h - 1.3 * inch, "No diagram uploaded yet.")

    # Attachments page
    c.showPage()
    header("Attachments")
    y = h - 1.3 * inch
    c.setFont("Helvetica", 10)
    if attachments:
        for a in attachments[:60]:
            fname = os.path.basename(a.file_path or "")
            kind = (a.kind or "").strip()
            label = f"- {fname}" + (f" [{kind}]" if kind else "")
            c.drawString(0.85 * inch, y, label[:130])
            y -= 0.18 * inch
            if y < 1.1 * inch:
                c.showPage()
                header("Attachments (cont.)")
                y = h - 1.3 * inch
    else:
        c.drawString(0.85 * inch, y, "- (none)")

    c.save()
