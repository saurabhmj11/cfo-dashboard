import asyncio
import os
import requests
import logging
from typing import Dict, Any
from app.services.agents.orchestrator import FinancialOrchestrator
from app.models.schemas import AnalysisPayload
from app.database import SessionLocal
from app.models.db_models import AnalysisRun, Transaction
from app.services.analytics.analytics import AnalyticsEngine

logger = logging.getLogger("Paperclip_Worker")

class PaperclipMonolithWorker:
    """
    Monolithic version of the Paperclip Adapter.
    Runs the agent loop directly inside the main app.
    """
    def __init__(self):
        self.paperclip_url = os.getenv("PAPERCLIP_URL", "http://paperclip:3100")
        self.company_id = os.getenv("PAPERCLIP_COMPANY_ID")
        self.agent_id = os.getenv("PAPERCLIP_AGENT_ID")
        self.orchestrator = FinancialOrchestrator()
        self.analytics = AnalyticsEngine()
        self.is_running = False

    async def start(self):
        self.is_running = True
        logger.info(f"Starting Paperclip Monolith Worker for Agent: {self.agent_id}")
        
        while self.is_running:
            try:
                await self._poll_and_execute()
            except Exception as e:
                logger.error(f"Error in Paperclip worker loop: {e}")
            
            await asyncio.sleep(10) # Poll every 10 seconds

    async def stop(self):
        self.is_running = False

    async def _poll_and_execute(self):
        if not self.company_id or not self.agent_id:
            logger.warning("Missing PAPERCLIP_COMPANY_ID or PAPERCLIP_AGENT_ID")
            return

        # 1. Fetch 'todo' issues
        url = f"{self.paperclip_url}/api/companies/{self.company_id}/issues?status=todo"
        res = requests.get(url)
        if res.status_code != 200:
            return

        issues = res.json()
        for issue in issues:
            # 2. Checkout the issue
            checkout_url = f"{self.paperclip_url}/api/issues/{issue['id']}/checkout"
            checkout_res = requests.post(checkout_url, json={"agentId": self.agent_id})
            
            if checkout_res.status_code == 201:
                logger.info(f"Checked out task: {issue['id']}")
                # 3. Execute Task (Direct Logic)
                await self._run_agent_task(issue)

    async def _run_agent_task(self, issue: Dict[str, Any]):
        issue_id = issue['id']
        payload_data = issue.get('payload', {})
        
        try:
            # For the monolith, we might need to fetch real data from DB based on run_id
            run_id = payload_data.get('run_id')
            
            with SessionLocal() as db:
                if run_id:
                    # Execute based on the full data context
                    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
                    transactions = db.query(Transaction).filter(Transaction.dataset_id == run.dataset_id).all()
                    analytics_results = self.analytics.compute_metrics(transactions)
                    data_payload = analytics_results["payload"]
                else:
                    # Fallback to payload if provided directly
                    data_payload = AnalysisPayload(**payload_data.get('tx_data', {}))

                # 4. Run AI Orchestrator
                ai_results = self.orchestrator.run_analysis(data_payload)
                
                # 5. Resolve in Paperclip
                resolve_url = f"{self.paperclip_url}/api/issues/{issue_id}/resolve"
                requests.patch(resolve_url, json={
                    "status": "done",
                    "comment": "Analysis completed successfully by monolithic agent coalition.",
                    "work_product": {
                        "detective": ai_results["detective_report"].model_dump(),
                        "forecast": ai_results["forecast_report"].model_dump(),
                        "advisor": ai_results["advisor_report"].model_dump()
                    }
                })
                logger.info(f"Resolved task: {issue_id}")

        except Exception as e:
            logger.error(f"Task Failed: {issue_id} - {e}")
            # Optional: resolve as failed in Paperclip
            requests.patch(f"{self.paperclip_url}/api/issues/{issue_id}/resolve", json={
                "status": "todo", # Put back in queue or mark failed
                "comment": f"Error: {str(e)}"
            })

# Singleton
paperclip_worker = PaperclipMonolithWorker()
