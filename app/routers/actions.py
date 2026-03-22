from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.dependencies import get_current_user
from app.models.db_models import User
from app.services.action_service import action_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/actions", tags=["Actions"])

class ActionResponse(BaseModel):
    id: int
    type: str # action_type
    title: str
    description: str
    payload: Dict[str, Any]
    status: str
    created_at: str

@router.get("/pending")
def get_pending_actions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    actions = action_service.get_pending_actions(db, user.id)
    return {
        "status": "success",
        "data": [
            {
                "id": a.id,
                "type": a.action_type,
                "title": a.title,
                "description": a.description,
                "payload": a.payload,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            } for a in actions
        ]
    }

class ExecutionRequest(BaseModel):
    action_id: int

@router.post("/execute")
def execute_action(
    req: ExecutionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = action_service.execute_action(db, user.id, req.action_id)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/reject")
def reject_action(
    req: ExecutionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    action_service.reject_action(db, user.id, req.action_id)
    return {"status": "success", "message": "Action rejected"}

# Debug Endpoint to seed a draft action
@router.post("/debug/seed")
def seed_debug_action(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    action_service.draft_action(
        db, user.id, "EMAIL", 
        "Renegotiate AWS Contract", 
        "Draft email to AWS Support requesting enterprise credits.", 
        {"to": "support@aws.amazon.com", "subject": "Enterprise Credit Request - TrustFinance", "body": "Dear Support..."}
    )
    return {"status": "seeded"}
