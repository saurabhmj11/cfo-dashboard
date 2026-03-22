from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from app.dependencies import get_current_user
from app.models.db_models import User
from app.services.connectors import connector_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

class ConnectRequest(BaseModel):
    provider_id: str
    api_key: str # In simulation, any string works

class DisconnectRequest(BaseModel):
    provider_id: str

@router.get("/")
def list_integrations(user: User = Depends(get_current_user)):
    return {
        "status": "success",
        "data": connector_service.get_all_integrations()
    }

@router.post("/connect")
def connect_integration(
    req: ConnectRequest,
    user: User = Depends(get_current_user)
):
    result = connector_service.connect_provider(req.provider_id, req.api_key)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/disconnect")
def disconnect_integration(
    req: DisconnectRequest,
    user: User = Depends(get_current_user)
):
    return connector_service.disconnect_provider(req.provider_id)

@router.post("/sync")
def sync_integration(
    req: DisconnectRequest, # Reusing simple prop provider_id
    user: User = Depends(get_current_user)
):
    return connector_service.trigger_sync(req.provider_id)
