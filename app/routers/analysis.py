from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.db_models import Dataset, AnalysisRun, User, Transaction
from app.models.schemas import FinancialAnalysisResult, DetectiveReport, ForecastReport, AdvisorReport
from app.models import schemas
from app.dependencies import get_current_user
from app.services.analytics.analytics import AnalyticsEngine
from app.services.analytics.wargame_engine import wargame_engine
from app.services.agents.orchestrator import FinancialOrchestrator
from app.services.audit import audit_service
from app.services.analytics.pipeline import run_monolith_analysis_pipeline
from fastapi import BackgroundTasks
import httpx
import os
import shutil
import uuid

router = APIRouter(prefix="/api/v1", tags=["Analysis"])

async def analyze_financial_data(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    tmp_path = f"temp_{uuid.uuid4()}.csv"
    try:
        # 1. Save File
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. User is now injected via Dependency


        # 3. Create Dataset Record
        dataset = Dataset(
            filename=file.filename,
            file_path=tmp_path, # In real app, S3 path
            user_id=user.id,
            tenant_id=user.tenant_id
        )
        db.add(dataset)
        db.commit()

        # 4. Layer 1: Validate & Clean
        validator = DataValidator()
        valid_records, errors = validator.validate_file(tmp_path, file.filename)
        
        # 5. Layer 2: Ingest into Golden Data Store (Transactions)
        created_transactions = []
        for record in valid_records:
            t = Transaction(
                dataset_id=dataset.id,
                txn_date=record.date, # Map date -> txn_date
                revenue=record.revenue,
                expenses=record.expenses,
                category=record.category
            )
            created_transactions.append(t)
            db.add(t)
        db.commit()
        
        # 6. Create Pending AnalysisRun
        analysis_run = AnalysisRun(
            user_id=user.id,
            tenant_id=user.tenant_id,
            dataset_id=dataset.id,
            metrics_result={},
            forecast_result={},
            advisor_result={},
            status="PROCESSING"
        )
        db.add(analysis_run)
        db.commit()
        api_run_id = analysis_run.id
        
        # 7. Start Async pipeline directly (Monolith)
        background_tasks.add_task(
            run_monolith_analysis_pipeline,
            db_session_factory=get_db, # We need a factory for new threads
            run_id=api_run_id,
            dataset_id=dataset.id,
            tenant_id=user.tenant_id,
            user_id=user.id
        )

        # --- Layer 7: Audit Log ---
        audit_service.log_action(
            db, 
            user_id=user.id, 
            action="ANALYSIS_QUEUED", 
            resource_id=str(api_run_id),
            details=f"Queued {len(valid_records)} rows from {file.filename} for processing"
        )
        
        # 8. Return immediately (202 Accepted logic)
        return {
            "status": "processing",
            "run_id": api_run_id,
            "message": "File ingested. Analytics running in background.",
            "data_quality": {
                "rows_processed": len(valid_records),
                "valid": True
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

@router.get("/latest")
def get_latest_analysis(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    run = db.query(AnalysisRun).filter(AnalysisRun.user_id == user.id).order_by(AnalysisRun.run_date.desc()).first()
    if not run:
        return {"status": "no_data"}
    
    return {
        "status": run.status.lower(),
        "error_message": run.error_message,
        "data": {
            "metrics": run.metrics_result, # Contains financials and detective
            "forecast": run.forecast_result,
            "advisor": run.advisor_result,
            "run_id": run.id,
            "run_date": run.run_date
        }
    }

@router.get("/latest/financials")
def get_latest_financials(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Fast endpoint: Only returns metrics and charts"""
    run = db.query(AnalysisRun).filter(AnalysisRun.tenant_id == user.tenant_id).order_by(AnalysisRun.run_date.desc()).first()
    if not run:
        return {"status": "no_data"}
    
    return {
        "status": run.status.lower(),
        "error_message": run.error_message,
        "data": {
            "metrics": run.metrics_result, 
            "forecast": run.forecast_result,
            "run_id": run.id
        }
    }

@router.get("/latest/advisor")
def get_latest_advisor(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Slow endpoint: Returns LLM advice"""
    run = db.query(AnalysisRun).filter(AnalysisRun.tenant_id == user.tenant_id).order_by(AnalysisRun.run_date.desc()).first()
    if not run:
        return {"status": "no_data"}
    
    return {
        "status": "success",
        "data": {
            "advisor": run.advisor_result
        }
    }

@router.get("/report/{run_id}/export")
def export_report(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    run = db.query(AnalysisRun).filter(
        AnalysisRun.id == run_id, 
        AnalysisRun.tenant_id == user.tenant_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    
    pdf_buffer = report_generator.generate_pdf(run)
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{run_id}.pdf"}
    )

class SimulationSetup(BaseModel):
    scenario_name: str
    growth_factor: float = 1.0 # 1.10 = +10%
    churn_factor: float = 0.0 # 0.05 = 5% chance

@router.post("/simulate")
def run_simulation(
    setup: SimulationSetup,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # 1. Get Baseline (Latest Real Run)
    run = db.query(AnalysisRun).filter(AnalysisRun.tenant_id == user.tenant_id).order_by(AnalysisRun.run_date.desc()).first()
    if not run:
        raise HTTPException(status_code=400, detail="Run an actual analysis first to establish a baseline.")
    
    # 2. Extract Baseline Metrics
    # Handle DB storage format (JSON vs dict)
    metrics = run.metrics_result if isinstance(run.metrics_result, dict) else dict(run.metrics_result)
    
    # 3. Use 'financials' key if present (new schema), else raw (legacy)
    financials = metrics.get("financials", metrics)

    # 4. Run Wargame (Direct Call)
    try:
        simulation_result = wargame_engine.simulate(
            baseline_metrics=financials,
            strategy=setup.scenario_name,
            growth_factor=setup.growth_factor,
            churn_factor=setup.churn_factor
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")
    
    return {
        "status": "success",
        "data": simulation_result
    }

@router.post("/simulate/commit")
def commit_simulation(
    setup: SimulationSetup,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Forks Reality: Saves the simulation as the new 'Latest Run'.
    """
    # 1. Get Baseline
    run = db.query(AnalysisRun).filter(AnalysisRun.tenant_id == user.tenant_id).order_by(AnalysisRun.run_date.desc()).first()
    if not run:
        raise HTTPException(status_code=400, detail="Run an actual analysis first.")
    
    metrics = run.metrics_result if isinstance(run.metrics_result, dict) else dict(run.metrics_result)
    financials = metrics.get("financials", metrics)

    # 2. Run Simulation (Direct Call)
    try:
        simulation_result = wargame_engine.simulate(
            baseline_metrics=financials,
            strategy=setup.scenario_name,
            growth_factor=setup.growth_factor,
            churn_factor=setup.churn_factor
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}")
    
    # 3. Create New AnalysisRun (The Fork)
    # We construct a synthetic 'metrics' object that looks like the real one but with simulated data
    # This allows the Frontend to render it natively without changes.
    
    sim_financials = {
        "monthly_data": simulation_result["monthly_projection"],
        "summary_revenue": simulation_result["summary"]["total_revenue"],
        "summary_expenses": simulation_result["summary"]["total_revenue"] - simulation_result["summary"]["total_profit"], # Backcalc
        "summary_profit": simulation_result["summary"]["total_profit"],
        "avg_margin": simulation_result["summary"]["avg_margin"]
    }
    
    sim_metrics = {
        "financials": sim_financials,
        "detective": {"observations": []}, # No detective in sim yet
        "is_simulation": True,
        "scenario_name": setup.scenario_name,
        "confidence_score": 0.8 # Lower confidence for sims
    }
    
    new_run = AnalysisRun(
        user_id=user.id,
        tenant_id=user.tenant_id,
        dataset_id=run.dataset_id,
        metrics_result=sim_metrics,
        forecast_result=simulation_result, # Store full sim details here
        advisor_result={"strategic_advice": []},
        run_date=datetime.now()
    )
    db.add(new_run)
    db.commit()
    
    return {
        "status": "success",
        "run_id": new_run.id,
        "message": f"Scenario '{setup.scenario_name}' saved as new forecast."
    }
