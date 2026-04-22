from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
from docx import Document


def convert_docx_to_pdf(docx_path, pdf_path):
    doc = Document(docx_path)
    pdf = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'CustomNormal', parent=styles['Normal'],
        fontSize=11, leading=14, alignment=TA_LEFT
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading1'],
        fontSize=14, leading=18, spaceAfter=6
    )
    story = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            story.append(Spacer(1, 0.3*cm))
            continue
        if para.style.name.startswith('Heading'):
            story.append(Paragraph(text, heading_style))
        else:
            story.append(Paragraph(text, normal_style))
        story.append(Spacer(1, 0.1*cm))
    pdf.build(story)
