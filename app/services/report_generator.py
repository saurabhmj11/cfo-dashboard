from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from app.models.db_models import AnalysisRun
import json

class ReportGenerator:
    def generate_pdf(self, run: AnalysisRun) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = styles['Title']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Data Extraction
        metrics = run.metrics_result if isinstance(run.metrics_result, dict) else json.loads(run.metrics_result)
        # Handle new schema (nested in 'financials'/'detective') or legacy
        if "detective" in metrics:
            detective = metrics["detective"]
            financials = metrics["financials"]
        else:
            detective = metrics # legacy fallback
            financials = metrics # legacy fallback (might fail if schema mismatch, but we handle robustly)

        advisor = run.advisor_result if isinstance(run.advisor_result, dict) else json.loads(run.advisor_result)
        
        # --- Content Construction ---
        
        # 1. Header
        story.append(Paragraph("AI Financial Analyst Report", title_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Run ID: {run.id} | Date: {run.run_date.strftime('%Y-%m-%d')}", normal_style))
        story.append(Spacer(1, 24))
        
        # 2. Executive Summary (The Narrative)
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Spacer(1, 6))
        summary_text = detective.get("summary", "No summary available.")
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 18))
        
        # 3. Key Observations
        story.append(Paragraph("Key Observations", heading_style))
        story.append(Spacer(1, 6))
        observations = detective.get("observations", [])
        if observations:
            obs_data = [["Metric", "Trend", "Detail"]]
            for obs in observations:
                obs_data.append([
                    obs.get("metric", ""),
                    obs.get("trend", ""),
                    Paragraph(obs.get("detail", ""), normal_style) # Wrap text
                ])
            
            t = Table(obs_data, colWidths=[80, 80, 300])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(t)
        else:
             story.append(Paragraph("No specific observations found.", normal_style))
        
        story.append(Spacer(1, 18))

        # 4. Financial Performance (Detailed Table)
        story.append(Paragraph("Financial Performance", heading_style))
        story.append(Spacer(1, 6))
        
        monthly_data = financials.get("monthly_data", [])
        if monthly_data:
            # Header
            fin_data = [["Month", "Revenue", "Expenses", "Net Profit", "Margin %"]]
            for m in monthly_data:
                # Handle dict or object
                rev = m.get("revenue", 0) if isinstance(m, dict) else getattr(m, "revenue", 0)
                exp = m.get("expenses", 0) if isinstance(m, dict) else getattr(m, "expenses", 0)
                prof = m.get("net_profit", 0) if isinstance(m, dict) else getattr(m, "net_profit", 0)
                margin = (prof / rev * 100) if rev else 0
                
                fin_data.append([
                    m.get("month", "N/A") if isinstance(m, dict) else getattr(m, "month", "N/A"),
                    f"${rev:,.0f}",
                    f"${exp:,.0f}",
                    f"${prof:,.0f}",
                    f"{margin:.1f}%"
                ])
                
            t_fin = Table(fin_data, colWidths=[80, 100, 100, 100, 80])
            t_fin.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")), # Slate-900
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'), # Align Month Left
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f8fafc")), # Slate-50
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ]))
            story.append(t_fin)
            story.append(Spacer(1, 18))
            
        # 5. Strategic Advice
        story.append(Paragraph("Strategic Advice", heading_style))
        story.append(Spacer(1, 6))
        advice_list = advisor.get("strategic_advice", [])
        for item in advice_list:
            p = Paragraph(f"<b>{item.get('decision')}</b>: {item.get('impact')}", normal_style)
            story.append(p)
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)
        return buffer

report_generator = ReportGenerator()
