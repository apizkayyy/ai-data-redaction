"""
Generates a realistic sample PDF with Malaysian PII for testing the masking service.

Run:
    python create_test_pdf.py
    python masking_service.py sample_document.pdf sample_masked.pdf --verbose
"""

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

OUTPUT = "sample_document.pdf"

PAGES = [
    # Page 1 – Employee onboarding form
    [
        ("Title",    "Employee Onboarding Form"),
        ("Heading2", "Personal Information"),
        ("Normal",   "Full Name: Ahmad Zulkifli bin Abdullah"),
        ("Normal",   "IC Number: 900112-14-5678"),
        ("Normal",   "Passport: A12345678"),
        ("Heading2", "Contact Details"),
        ("Normal",   "Mobile: +60 12-345 6789"),
        ("Normal",   "Work Email: ahmad.zulkifli@techcorp.com.my"),
        ("Normal",   "Home Address: No 14, Jalan Taman Maju, 47810 Petaling Jaya, Selangor"),
        ("Heading2", "Banking Details"),
        ("Normal",   "Bank: Maybank Berhad"),
        ("Normal",   "Account Number: 1234-5678-9012"),
        ("Normal",   "Credit Card: 4111 1111 1111 1111 (Visa)"),
        ("Heading2", "Emergency Contact"),
        ("Normal",   "Name: Siti Rahimah binti Ismail"),
        ("Normal",   "Relationship: Spouse"),
        ("Normal",   "Phone: +60 11-9876 5432"),
        ("Heading2", "Declaration"),
        ("Normal",
         "I, Ahmad Zulkifli bin Abdullah (IC: 900112-14-5678), confirm that "
         "the information above is accurate. Submitted on 15 July 2026 at our "
         "Petaling Jaya headquarters, Selangor."),
    ],
    # Page 2 – Invoice
    [
        ("Title",    "Tax Invoice #INV-2026-0715"),
        ("Heading2", "Bill To"),
        ("Normal",   "Company: TechCorp Solutions Sdn. Bhd."),
        ("Normal",   "Contact: Lim Mei Ling"),
        ("Normal",   "Email: meiling.lim@techcorp.com.my"),
        ("Normal",   "Phone: 03-2345 6789"),
        ("Normal",   "Address: Level 5, Menara Commerce, Jalan Raja Chulan, 50200 Kuala Lumpur"),
        ("Heading2", "Payment Details"),
        ("Normal",   "Bank: CIMB Bank"),
        ("Normal",   "Account: 8012-3456-7890"),
        ("Normal",   "SWIFT: CIBBMYKL"),
        ("Normal",   "Reference: INV-2026-0715 / Lim Mei Ling"),
        ("Heading2", "Remarks"),
        ("Normal",
         "Please transfer RM 5,500.00 to account 8012-3456-7890 before 30 July 2026. "
         "For queries, contact meiling.lim@techcorp.com.my or call 03-2345 6789."),
    ],
]


def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    for page_content in PAGES:
        for style_name, text in page_content:
            story.append(Paragraph(text, styles[style_name]))
            story.append(Spacer(1, 0.3*cm))
        # Page break between pages (add extra space to force new page)
        story.append(Spacer(1, 5*cm))

    doc.build(story)
    print(f"✓ Created: {OUTPUT}")


if __name__ == "__main__":
    build()
