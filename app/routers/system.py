from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.services.audit import audit_service
from app.models.db_models import InsightFeedback, User
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/api/v1/system",
    tags=["system"]
)

class FeedbackRequest(BaseModel):
    user_id: int
    analysis_run_id: int
    insight_text: str
    feedback_type: str # "APPROVE", "REJECT"
    comments: str = ""

@router.post("/feedback")
def submit_feedback(
    request: FeedbackRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Human-in-the-Loop Endpoint.
    Allows users (CFOs) to approve or reject AI insights.
    """
    # 1. User is validated by dependency
    user = current_user

    # 2. Record Feedback
    feedback = InsightFeedback(
        user_id=user.id,
        analysis_run_id=request.analysis_run_id,
        insight_text=request.insight_text,
        feedback_type=request.feedback_type,
        comments=request.comments
    )
    db.add(feedback)
    db.commit()
    
    # 3. Audit The Feedback (Meta-Audit)
    audit_service.log_action(
        db, 
        user_id=user.id, 
        action="FEEDBACK_SUBMITTED", 
        resource_id=str(request.analysis_run_id), 
        details=f"{request.feedback_type}: {request.insight_text[:50]}..."
    )
    
    return {"status": "success", "message": "Feedback recorded"}
