from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.db_models import User
from app.services.memory_service import memory_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])

class FeedbackRequest(BaseModel):
    run_id: int
    insight_text: str
    feedback_type: str # "THUMBS_UP", "THUMBS_DOWN"
    comments: str = None

@router.post("/")
def submit_feedback(
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    try:
        memory_service.store_feedback(
            db, 
            user.id, 
            req.run_id, 
            req.insight_text, 
            req.feedback_type, 
            req.comments
        )
        return {"status": "success", "message": "Feedback recorded. The AI will learn from this."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
