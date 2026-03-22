from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from app.consumer import start_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_consumer())
    yield
    task.cancel()
from typing import Dict, Any

from app.models.schemas import AnalysisPayload
from app.services.agents.orchestrator import FinancialOrchestrator

app = FastAPI(
    title="AI Orchestrator Service", 
    version="1.0.0", 
    description="Independent GenAI layer for deep anomaly investigation.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = FinancialOrchestrator()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai_orchestrator"}

@app.post("/api/v1/agents/analyze")
async def perform_deep_analysis(payload: AnalysisPayload) -> Dict[str, Any]:
    """
    Receives deterministic anomalies & KPIs from the Analytics Engine.
    Dispatches the AI Agent Coalition to generate insights.
    """
    try:
        # Note: If this reaches here, the Analytics Engine has already 
        # computed that `payload` contains anomalies.
        print(f"[AI ORCHESTRATOR] Received payload with {len(payload.anomalies)} anomalies. Engaging Generation.")
        
        result = orchestrator.run_analysis(payload)
        
        return {
            "status": "success",
            "message": "AI generation complete.",
            "data": result
        }
    except Exception as e:
        print(f"Error in deep analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
