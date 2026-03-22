from fastapi import FastAPI
from app.routers import analysis, chat, system, auth, actions, integrations, feedback, ingestion, market, search, reports
import asyncio
from contextlib import asynccontextmanager
from app.services.consumer import start_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_consumer())
    yield
    task.cancel()

app = FastAPI(title="AI Financial Analyst API", version="1.6.0", lifespan=lifespan)

# Global Exception Handler
from fastapi.responses import JSONResponse
from fastapi.requests import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}", "path": request.url.path},
    )

# Enable CORS for Next.js Frontend
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(analysis.router)
app.include_router(chat.router)
app.include_router(system.router)
app.include_router(actions.router)
app.include_router(integrations.router)
app.include_router(feedback.router)
app.include_router(ingestion.router)
app.include_router(market.router)
app.include_router(search.router)
app.include_router(reports.router)

# Create Database Tables
from app.database import engine
from app.models import db_models
db_models.Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"message": "AI Financial Analyst API is running. Docs at /docs"}
