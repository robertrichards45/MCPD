import os
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


def append_signature_page(original_pdf, signature_png, signer_name, signed_at, output_pdf):
    tmp_page = output_pdf + '.sigpage.pdf'
    c = canvas.Canvas(tmp_page, pagesize=letter)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(40, 750, 'Training Roster Signature')
    c.setFont('Helvetica', 11)
    c.drawString(40, 720, f'Name: {signer_name}')
    c.drawString(40, 700, f'Signed At: {signed_at}')
    c.drawString(40, 680, 'Signature:')
    if os.path.exists(signature_png):
        c.drawImage(signature_png, 40, 600, width=200, height=60, preserveAspectRatio=True, mask='auto')
    c.showPage()
    c.save()

    writer = PdfWriter()
    for p in PdfReader(original_pdf).pages:
        writer.add_page(p)
    for p in PdfReader(tmp_page).pages:
        writer.add_page(p)

    with open(output_pdf, 'wb') as f:
        writer.write(f)

    os.remove(tmp_page)
