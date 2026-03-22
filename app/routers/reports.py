"""
Reports Router
Export financial reports as PDF or Excel.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.services.report_service import report_service
from app.dependencies import get_current_user
from app.models.db_models import User

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"]
)


class ReportRequest(BaseModel):
    title: str = Field("Financial Analysis Report", description="Report title")
    analysis_data: Dict[str, Any] = Field(..., description="Analysis data to include")
    format: str = Field("pdf", description="Export format: pdf or excel")
    include_transactions: bool = Field(False, description="Include transaction details")
    transactions: Optional[List[Dict]] = Field(None, description="Transaction data")


@router.get("/formats")
async def get_available_formats():
    """Get available export formats."""
    return {
        "formats": [
            {
                "id": "pdf",
                "name": "PDF Report",
                "available": report_service.is_available,
                "description": "Professional PDF with charts and summaries"
            },
            {
                "id": "excel",
                "name": "Excel Workbook",
                "available": report_service.is_available,
                "description": "Multi-sheet Excel with raw data"
            }
        ]
    }


@router.post("/generate")
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate a downloadable report.
    
    Example:
    ```json
    {
        "title": "Q4 Financial Analysis",
        "format": "pdf",
        "analysis_data": {
            "detective_report": {...},
            "forecast_report": {...},
            "advisor_report": {...}
        }
    }
    ```
    """
    if not report_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="Report service unavailable. Install: pip install reportlab xlsxwriter"
        )
    
    if request.format == "pdf":
        buffer = report_service.generate_pdf(
            title=request.title,
            analysis_data=request.analysis_data
        )
        
        if not buffer:
            raise HTTPException(status_code=500, detail="Failed to generate PDF")
        
        filename = f"report_{request.title.replace(' ', '_')}.pdf"
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    elif request.format == "excel":
        buffer = report_service.generate_excel(
            title=request.title,
            analysis_data=request.analysis_data,
            transactions=request.transactions
        )
        
        if not buffer:
            raise HTTPException(status_code=500, detail="Failed to generate Excel")
        
        filename = f"report_{request.title.replace(' ', '_')}.xlsx"
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {request.format}. Use 'pdf' or 'excel'"
        )


@router.post("/quick-pdf")
async def quick_pdf_export(
    title: str = "Analysis Report",
    current_user: User = Depends(get_current_user)
):
    """
    Generate a quick PDF with sample/demo data.
    Useful for testing the export functionality.
    """
    sample_data = {
        "detective_report": {
            "metrics": {
                "total_revenue": 1250000,
                "total_expenses": 875000,
                "net_profit": 375000,
                "profit_margin": 30.0
            }
        },
        "risk_report": {
            "overall_score": 45,
            "risk_level": "Medium",
            "metrics": {
                "var_95": 12500,
                "var_99": 18750,
                "sharpe_ratio": 1.2,
                "volatility": 0.18
            },
            "warnings": ["Portfolio volatility approaching threshold"]
        },
        "advisor_report": {
            "summary": "The company shows strong financial health with a 30% profit margin.",
            "recommendations": [
                "Consider expanding into new markets",
                "Invest in automation to reduce operational costs",
                "Build a 6-month cash reserve"
            ]
        }
    }
    
    buffer = report_service.generate_pdf(title=title, analysis_data=sample_data)
    
    if not buffer:
        raise HTTPException(status_code=500, detail="PDF generation failed")
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="quick_report.pdf"'
        }
    )
