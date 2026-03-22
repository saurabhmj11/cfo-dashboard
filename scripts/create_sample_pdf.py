from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
import os
import random
from datetime import datetime, timedelta

def create_bank_statement():
    # Ensure output directory exists
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "tests", "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "sample_bank_statement.pdf")
    
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # 1. Header
    story.append(Paragraph("<b>GLOBAL TRUST BANK - BUSINESS CHECKING</b>", styles['Heading1']))
    story.append(Paragraph("Account: 123-456-7890 | Statement Period: Jan 01 2024 - Jan 31 2024", styles['Normal']))
    story.append(Spacer(1, 24))

    # 2. Summary
    story.append(Paragraph("<b>Account Summary</b>", styles['Heading3']))
    summary_data = [
        ["Opening Balance", "$124,500.00"],
        ["Total Deposits", "$145,200.00"],
        ["Total Withdrawals", "$89,450.00"],
        ["Closing Balance", "$180,250.00"]
    ]
    t_summary = Table(summary_data, colWidths=[200, 100])
    t_summary.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 24))

    # 3. Transactions
    story.append(Paragraph("<b>Transaction Activity</b>", styles['Heading3']))
    story.append(Spacer(1, 12))

    # Headers
    data = [["Date", "Description", "Type", "Amount", "Balance"]]
    
    # Generate Mock Data
    current_date = datetime(2024, 1, 1)
    balance = 124500.00
    
    descriptions = [
        ("Client Payment - Acme Corp", "CR", 15000),
        ("AWS Web Services", "DR", -2400),
        ("Payroll Withdrawal", "DR", -18000),
        ("Stripe Payout #9923", "CR", 8500),
        ("Office Lease", "DR", -3500),
        ("Consulting Fees - Beta Ltd", "CR", 12000),
        ("Software Subscription", "DR", -150),
        ("Marketing Google Ads", "DR", -4200),
        ("Client Payment - Gamma Inc", "CR", 22000),
        ("Utility Bill", "DR", -450),
        ("Stripe Payout #9924", "CR", 9200),
        ("Contractor Payment", "DR", -1200)
    ]

    for desc, txn_type, amount in descriptions:
        current_date += timedelta(days=random.randint(1, 3))
        balance += amount
        amt_str = f"${abs(amount):,.2f}"
        
        # In bank statements, debits are often plain or brackets, credits specific
        # We'll use a standard format
        if amount < 0:
            amt_display = f"({abs(amount):,.2f})"
        else:
            amt_display = f"{amount:,.2f}"
            
        data.append([
            current_date.strftime("%Y-%m-%d"),
            desc,
            "DEBIT" if amount < 0 else "CREDIT",
            amt_display,
            f"${balance:,.2f}"
        ])

    # Table Styling
    t = Table(data, colWidths=[80, 200, 60, 80, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'), # Amounts right aligned
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    story.append(t)
    doc.build(story)
    print(f"PDF generated at: {output_path}")

if __name__ == "__main__":
    create_bank_statement()
