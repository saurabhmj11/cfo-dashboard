"""
Report Export Service
Generate PDF and Excel reports from analysis data.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from io import BytesIO
import json

# PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("[REPORT] reportlab not installed. Run: pip install reportlab")

# Excel generation
try:
    import xlsxwriter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("[REPORT] xlsxwriter not installed. Run: pip install xlsxwriter")


class ReportService:
    """
    Generate professional PDF and Excel reports from financial analysis.
    """
    
    def __init__(self):
        self.company_name = "AI Financial Analyst"
        self.version = "1.6"
    
    @property
    def is_available(self) -> bool:
        return PDF_AVAILABLE or EXCEL_AVAILABLE
    
    def generate_pdf(
        self,
        title: str,
        analysis_data: Dict[str, Any],
        include_charts: bool = False
    ) -> Optional[BytesIO]:
        """
        Generate a professional PDF report.
        
        Args:
            title: Report title
            analysis_data: Financial analysis results
            include_charts: Whether to include chart images (if available)
        
        Returns:
            BytesIO buffer containing PDF data
        """
        if not PDF_AVAILABLE:
            return None
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a365d')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2d3748')
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8
        )
        
        # Header
        story.append(Paragraph(self.company_name, styles['Normal']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.gray)
        ))
        story.append(Spacer(1, 30))
        
        # Executive Summary
        if 'advisor_report' in analysis_data:
            advisor = analysis_data['advisor_report']
            story.append(Paragraph("Executive Summary", heading_style))
            
            if hasattr(advisor, 'summary') and advisor.summary:
                story.append(Paragraph(advisor.summary, body_style))
            elif isinstance(advisor, dict) and 'summary' in advisor:
                story.append(Paragraph(advisor['summary'], body_style))
            
            story.append(Spacer(1, 20))
        
        # Key Metrics
        if 'detective_report' in analysis_data:
            detective = analysis_data['detective_report']
            story.append(Paragraph("Key Financial Metrics", heading_style))
            
            metrics_data = []
            if hasattr(detective, 'metrics'):
                metrics = detective.metrics
                metrics_data = [
                    ["Metric", "Value"],
                    ["Total Revenue", f"${metrics.total_revenue:,.2f}" if hasattr(metrics, 'total_revenue') else "N/A"],
                    ["Total Expenses", f"${metrics.total_expenses:,.2f}" if hasattr(metrics, 'total_expenses') else "N/A"],
                    ["Net Profit", f"${metrics.net_profit:,.2f}" if hasattr(metrics, 'net_profit') else "N/A"],
                    ["Profit Margin", f"{metrics.profit_margin:.1f}%" if hasattr(metrics, 'profit_margin') else "N/A"],
                ]
            elif isinstance(detective, dict) and 'metrics' in detective:
                m = detective['metrics']
                metrics_data = [
                    ["Metric", "Value"],
                    ["Total Revenue", f"${m.get('total_revenue', 0):,.2f}"],
                    ["Total Expenses", f"${m.get('total_expenses', 0):,.2f}"],
                    ["Net Profit", f"${m.get('net_profit', 0):,.2f}"],
                    ["Profit Margin", f"{m.get('profit_margin', 0):.1f}%"],
                ]
            
            if metrics_data:
                table = Table(metrics_data, colWidths=[3*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('TOPPADDING', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ]))
                story.append(table)
            
            story.append(Spacer(1, 20))
        
        # Forecast Section
        if 'forecast_report' in analysis_data:
            forecast = analysis_data['forecast_report']
            story.append(Paragraph("Financial Forecast", heading_style))
            
            if isinstance(forecast, dict):
                if 'summary' in forecast:
                    story.append(Paragraph(forecast['summary'], body_style))
                if 'predictions' in forecast:
                    for pred in forecast['predictions'][:5]:
                        story.append(Paragraph(f"• {pred}", body_style))
            
            story.append(Spacer(1, 20))
        
        # Risk Analysis
        if 'risk_report' in analysis_data:
            risk = analysis_data['risk_report']
            story.append(Paragraph("Risk Assessment", heading_style))
            
            if isinstance(risk, dict):
                risk_level = risk.get('risk_level', 'Unknown')
                risk_score = risk.get('overall_score', 0)
                story.append(Paragraph(
                    f"<b>Risk Level:</b> {risk_level} (Score: {risk_score}/100)",
                    body_style
                ))
                
                metrics = risk.get('metrics', {})
                if metrics:
                    story.append(Paragraph(f"• VaR (95%): ${metrics.get('var_95', 0):,.2f}", body_style))
                    story.append(Paragraph(f"• Sharpe Ratio: {metrics.get('sharpe_ratio', 'N/A')}", body_style))
                
                warnings = risk.get('warnings', [])
                if warnings:
                    story.append(Paragraph("<b>Warnings:</b>", body_style))
                    for w in warnings:
                        story.append(Paragraph(f"⚠️ {w}", body_style))
            
            story.append(Spacer(1, 20))
        
        # Recommendations
        if 'advisor_report' in analysis_data:
            advisor = analysis_data['advisor_report']
            recommendations = []
            
            if hasattr(advisor, 'recommendations'):
                recommendations = advisor.recommendations
            elif isinstance(advisor, dict) and 'recommendations' in advisor:
                recommendations = advisor['recommendations']
            
            if recommendations:
                story.append(Paragraph("Strategic Recommendations", heading_style))
                for i, rec in enumerate(recommendations[:5], 1):
                    story.append(Paragraph(f"{i}. {rec}", body_style))
        
        # Footer
        story.append(Spacer(1, 40))
        story.append(Paragraph(
            f"Report generated by {self.company_name} v{self.version}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
        ))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_excel(
        self,
        title: str,
        analysis_data: Dict[str, Any],
        transactions: Optional[List[Dict]] = None
    ) -> Optional[BytesIO]:
        """
        Generate an Excel report with multiple sheets.
        
        Args:
            title: Report title
            analysis_data: Financial analysis results
            transactions: Optional list of transaction data
        
        Returns:
            BytesIO buffer containing Excel data
        """
        if not EXCEL_AVAILABLE:
            return None
        
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#1a365d',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'border': 1
        })
        
        percent_format = workbook.add_format({
            'num_format': '0.0%',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1
        })
        
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': '#1a365d'
        })
        
        # === Summary Sheet ===
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.set_column('A:A', 25)
        summary_sheet.set_column('B:B', 20)
        
        summary_sheet.write('A1', title, title_format)
        summary_sheet.write('A2', f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        row = 4
        
        # Key Metrics
        if 'detective_report' in analysis_data:
            detective = analysis_data['detective_report']
            summary_sheet.write(row, 0, 'Key Metrics', header_format)
            summary_sheet.write(row, 1, 'Value', header_format)
            row += 1
            
            metrics = detective.get('metrics', detective) if isinstance(detective, dict) else {}
            if hasattr(detective, 'metrics'):
                metrics = {
                    'total_revenue': getattr(detective.metrics, 'total_revenue', 0),
                    'total_expenses': getattr(detective.metrics, 'total_expenses', 0),
                    'net_profit': getattr(detective.metrics, 'net_profit', 0),
                    'profit_margin': getattr(detective.metrics, 'profit_margin', 0),
                }
            elif isinstance(metrics, dict) and 'metrics' in metrics:
                metrics = metrics['metrics']
            
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    summary_sheet.write(row, 0, key.replace('_', ' ').title(), cell_format)
                    if 'margin' in key or 'ratio' in key or 'percent' in key:
                        summary_sheet.write(row, 1, value / 100, percent_format)
                    else:
                        summary_sheet.write(row, 1, value, money_format)
                    row += 1
        
        row += 2
        
        # Risk Metrics
        if 'risk_report' in analysis_data:
            risk = analysis_data['risk_report']
            if isinstance(risk, dict):
                summary_sheet.write(row, 0, 'Risk Metrics', header_format)
                summary_sheet.write(row, 1, 'Value', header_format)
                row += 1
                
                summary_sheet.write(row, 0, 'Risk Score', cell_format)
                summary_sheet.write(row, 1, risk.get('overall_score', 0), cell_format)
                row += 1
                
                summary_sheet.write(row, 0, 'Risk Level', cell_format)
                summary_sheet.write(row, 1, risk.get('risk_level', 'Unknown'), cell_format)
                row += 1
                
                metrics = risk.get('metrics', {})
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        summary_sheet.write(row, 0, key.replace('_', ' ').title(), cell_format)
                        summary_sheet.write(row, 1, value, money_format if 'var' in key else cell_format)
                        row += 1
        
        # === Transactions Sheet ===
        if transactions:
            txn_sheet = workbook.add_worksheet('Transactions')
            txn_sheet.set_column('A:A', 12)
            txn_sheet.set_column('B:B', 30)
            txn_sheet.set_column('C:D', 15)
            
            headers = ['Date', 'Description', 'Credit', 'Debit']
            for col, header in enumerate(headers):
                txn_sheet.write(0, col, header, header_format)
            
            for row, txn in enumerate(transactions, 1):
                txn_sheet.write(row, 0, txn.get('date', ''), cell_format)
                txn_sheet.write(row, 1, txn.get('description', ''), cell_format)
                txn_sheet.write(row, 2, txn.get('credit', 0), money_format)
                txn_sheet.write(row, 3, txn.get('debit', 0), money_format)
        
        workbook.close()
        buffer.seek(0)
        return buffer


# Singleton instance
report_service = ReportService()
