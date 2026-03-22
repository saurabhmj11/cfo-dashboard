from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from app.consumer import start_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_consumer())
    yield
    task.cancel()
from typing import Dict, Any, List

from app.models.schemas import TransactionBase, AnalysisPayload, SimulationSetup
from app.services.analytics import AnalyticsEngine
from app.services.wargame_engine import wargame_engine

app = FastAPI(
    title="Analytics Engine Service", 
    version="1.0.0", 
    description="Deterministic math layer for aggregation, anomalies, and wargame simulations.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = AnalyticsEngine()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics_engine"}

@app.post("/api/v1/compute-metrics")
async def compute_metrics(transactions: List[TransactionBase]) -> Dict[str, Any]:
    """
    Takes pure transaction data, outputs calculated KPIs and detected anomalies.
    Does NOT call LLMs.
    """
    try:
        # Analytics Engine expects mock ORM objects or dicts. 
        # Using the base schemas directly works as long as fields match.
        result = engine.compute_metrics(transactions)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        print(f"[Analytics] Error computing metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/simulate")
async def simulate_scenario(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs a deterministic math scenario on top of baseline metrics.
    """
    try:
        baseline = payload.get("baseline_metrics", {})
        setup = payload.get("setup", {})
        
        sim_result = wargame_engine.simulate(
            baseline_metrics=baseline,
            strategy=setup.get("scenario_name", "Custom"),
            growth_factor=setup.get("growth_factor", 1.0),
            churn_factor=setup.get("churn_factor", 0.0)
        )
        return {
            "status": "success",
            "data": sim_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
