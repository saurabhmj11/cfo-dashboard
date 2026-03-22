from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import List
import shutil
import os
from datetime import datetime
from app.services.refinery import refinery_service
from app.database import get_db, SessionLocal
from app.models.db_models import Dataset, User
from app.models.db_models import Dataset, User, Transaction, AnalysisRun
from app.dependencies import get_current_user
from app.services.analytics import AnalyticsEngine
from app.services.agents.orchestrator import FinancialOrchestrator
from app.services.memory_service import memory_service
from app.services.audit import audit_service

router = APIRouter(
    prefix="/api/v1/ingestion",
    tags=["ingestion"]
)

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload/pdf")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Uploads a 'Messy' PDF Bank Statement.
    Triggers background refinery to creating 'Golden' Excel.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # 1. Save File
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Create Dataset Record
    dataset = Dataset(
        filename=safe_filename,
        file_path=file_path,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        is_golden=0 # Not yet refined
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # 3. Trigger Background Processing
    background_tasks.add_task(refinery_service.process_pdf, file_path, dataset.id)

    return {
        "status": "processing",
        "message": "File uploaded. Refining into Golden Data in background...",
        "dataset_id": dataset.id,
        "file_path": file_path
    }

@router.post("/upload/json")
async def upload_json(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Uploads a raw JSON file.
    Triggers background refinery to create 'Golden' Excel.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed")

    # 1. Save File
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Create Dataset Record
    dataset = Dataset(
        filename=safe_filename,
        file_path=file_path,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        is_golden=0 
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # 3. Trigger Background Processing
    background_tasks.add_task(refinery_service.process_json, file_path, dataset.id)

    return {
        "status": "processing",
        "message": "JSON uploaded. Refining into Golden Data in background...",
        "dataset_id": dataset.id,
        "file_path": file_path
    }

@router.get("/download/{dataset_id}")
async def download_golden_excel(dataset_id: int, db = Depends(get_db)):
    """
    Download the refined 'Golden' Excel file.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    golden_path = dataset.file_path.replace(".pdf", "_golden.xlsx")
    
    if not os.path.exists(golden_path):
        if dataset.is_golden == 0:
            return {"status": "processing", "message": "Still refining..."}
        raise HTTPException(status_code=404, detail="Golden file not found (Refinery failed?)")

    return FileResponse(
        path=golden_path, 
        filename=f"Golden_{dataset.filename.replace('.pdf', '.xlsx')}",
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@router.post("/promote/{dataset_id}")
async def promote_to_dashboard(
    dataset_id: int, 
    db = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Promotes a Refined Dataset to the Main Dashboard.
    Runs the full AI Analysis Pipeline (Analytics + Orchestrator) on existing transactions.
    """
    # 1. Verify Dataset
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.tenant_id == user.tenant_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")
        
    if dataset.is_golden == 0:
        raise HTTPException(status_code=400, detail="Data must be refined before promotion.")

    # 2. Fetch Transactions
    transactions = db.query(Transaction).filter(Transaction.dataset_id == dataset_id).all()
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions found for this dataset.")

    try:
        # 3. Layer 3: Deterministic Analytics
        engine = AnalyticsEngine()
        analytics_result = engine.compute_metrics(transactions)
        
        metrics = analytics_result["legacy"]
        payload = analytics_result["payload"]
        
        # 4. Layer 2.5: Agent Memory Context
        advisor_context = memory_service.get_advisor_context(db, user.id)

        # 5. Layer 4, 5, 6: AI Orchestration (The Triad)
        orchestrator = FinancialOrchestrator()
        ai_results = orchestrator.run_analysis(payload, context=advisor_context)
        
        detective_report = ai_results["detective_report"]
        forecast_report = ai_results["forecast_report"]
        advisor_report = ai_results["advisor_report"]

        # 6. Persist Run
        analysis_run = AnalysisRun(
            user_id=user.id,
            tenant_id=user.tenant_id,
            dataset_id=dataset.id,
            metrics_result={
                "financials": metrics.model_dump(mode='json'),
                "detective": detective_report.model_dump(mode='json')
            },
            forecast_result=forecast_report.model_dump(mode='json'),
            advisor_result=advisor_report.model_dump(mode='json')
        )
        db.add(analysis_run)
        db.commit()
        
        # 7. Audit Log
        audit_service.log_action(
            db, 
            user_id=user.id, 
            action="DATA_PROMOTION", 
            resource_id=str(analysis_run.id),
            details=f"Promoted dataset {dataset_id} to dashboard."
        )

        return {
            "status": "success",
            "run_id": analysis_run.id,
            "message": "Data successfully transformed to Executive Dashboard."
        }
    except Exception as e:
        print(f"Promotion Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
