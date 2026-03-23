from typing import Callable, Any
from sqlalchemy.orm import Session
from app.models.db_models import Transaction, AnalysisRun
from app.services.analytics.analytics import AnalyticsEngine
from app.services.agents.orchestrator import FinancialOrchestrator
import logging

logger = logging.getLogger("Monolith_Pipeline")

def run_monolith_analysis_pipeline(
    db_session_factory: Callable[[], Session],
    run_id: int,
    dataset_id: int,
    tenant_id: int,
    user_id: int
):
    """
    Unified, monolithic analysis pipeline.
    Replaces the distributed RabbitMQ workflow.
    """
    logger.info(f"[Monolith Pipeline] Starting analysis for run_id: {run_id}")
    db = db_session_factory()
    try:
        # 1. Fetch Transactions
        transactions = db.query(Transaction).filter(Transaction.dataset_id == dataset_id).all()
        if not transactions:
            logger.error(f"No transactions found for dataset_id: {dataset_id}")
            return

        # 2. Run Analytics Engine (Layer 3)
        analytics = AnalyticsEngine()
        results = analytics.compute_metrics(transactions)
        legacy_result = results["legacy"]
        payload = results["payload"]

        # 3. Run AI Orchestrator (Layer 4)
        orchestrator = FinancialOrchestrator()
        ai_results = orchestrator.run_analysis(payload)

        # 4. Update AnalysisRun
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = "COMPLETED"
            # Merge metrics and AI results for the UI
            run.metrics_result = {
                "financials": legacy_result.model_dump(),
                "detective": ai_results["detective_report"].model_dump()
            }
            run.forecast_result = ai_results["forecast_report"].model_dump()
            run.advisor_result = ai_results["advisor_report"].model_dump()
            
            db.commit()
            logger.info(f"Successfully completed analysis for run_id: {run_id}")
            
    except Exception as e:
        logger.error(f"Error in monolith analysis pipeline: {str(e)}")
        db.rollback()
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
        if run:
            run.status = "FAILED"
            run.error_message = str(e)
            db.commit()
    finally:
        db.close()
