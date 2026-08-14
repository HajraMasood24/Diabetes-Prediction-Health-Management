"""
Builds the downloadable PDF risk-assessment report for a user.
"""
import io
import datetime

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

_BRAND_COLOR = colors.HexColor('#5C2525')


def build_prediction_report_pdf(username, email, predictions, latest):
    """
    Build a PDF report and return it as a BytesIO buffer, ready to send.

    predictions: list of (timestamp, age, gender, bmi, glucose, prediction, probability)
    latest: (prediction, probability, timestamp) or None
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=24, textColor=_BRAND_COLOR, alignment=1, spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        'CustomHeading', parent=styles['Heading2'],
        fontSize=14, textColor=_BRAND_COLOR, spaceAfter=10, spaceBefore=15,
    )

    story.append(Paragraph("Diabetes Risk Assessment Report", title_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"<b>Patient Name:</b> {username}", styles['Normal']))
    story.append(Paragraph(f"<b>Email:</b> {email}", styles['Normal']))
    story.append(Paragraph(f"<b>Report Date:</b> {datetime.datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    if latest:
        story.append(Paragraph("Latest Risk Assessment", heading_style))
        risk_table = Table([
            ['Risk Level', 'HIGH RISK' if latest[0] == 'Diabetic' else 'Low Risk'],
            ['Probability', f"{latest[1]:.1%}"],
            ['Assessment Date', latest[2][:10]],
        ], colWidths=[2 * inch, 3 * inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F3F0')),
            ('TEXTCOLOR', (0, 0), (0, -1), _BRAND_COLOR),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Prediction History", heading_style))
    history_data = [['Date', 'Age', 'Gender', 'BMI', 'Glucose', 'Result', 'Risk']]
    for p in predictions[:10]:
        history_data.append([p[0][:10], str(p[1]), p[2], f"{p[3]:.1f}", str(p[4]), p[5], f"{p[6]:.1%}"])

    history_table = Table(
        history_data,
        colWidths=[0.9 * inch, 0.5 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch, 0.9 * inch, 0.8 * inch],
    )
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), _BRAND_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(history_table)

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("<b>Medical Disclaimer</b>", styles['Normal']))
    story.append(Paragraph(
        "This report is AI-generated and does not constitute medical diagnosis. "
        "Please consult a qualified healthcare professional.",
        styles['Italic'],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
