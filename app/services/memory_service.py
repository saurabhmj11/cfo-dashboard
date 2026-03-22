from sqlalchemy.orm import Session
from app.models.db_models import InsightFeedback, User
from app.models.schemas import AdvisorContext
from typing import List
from datetime import datetime

class MemoryService:
    """
    Retrieves historical context to personalize agent behavior.
    """
    
    def get_advisor_context(self, db: Session, user_id: int) -> AdvisorContext:
        """
        Builds the context object based on past user interactions.
        """
        # 1. Fetch Rejected Topics (Feedback Type = "REJECT")
        # We look for recurring rejections to avoid repeating them.
        rejected_feedback = db.query(InsightFeedback).filter(
            InsightFeedback.user_id == user_id,
            InsightFeedback.feedback_type == "REJECT"
        ).all()
        
        # Extract the 'decision' or 'topic' from the insight text or metadata
        # For this MVP, we'll assume the 'insight_text' itself or a parsed topic relies on simple string matching
        # In a real app, InsightFeedback would have a 'topic_tag' column.
        
        rejected_topics = []
        for feedback in rejected_feedback:
            # MVP: Use the whole text as a "do not repeat" hash, or extracting known keywords
            # For robustness, let's assume looking for distinct advice titles if we parsed them.
            # Here we just pass a list of strings to avoid.
            if feedback.insight_text:
                rejected_topics.append(feedback.insight_text)
                
        return AdvisorContext(
            rejected_topics=rejected_topics,
            preferred_strategy="Balanced"
        )

    def store_feedback(self, db: Session, user_id: int, run_id: int, insight_text: str, feedback_type: str, comments: str = None):
        """
        Stores user feedback for RLHF.
        """
        fb = InsightFeedback(
            user_id=user_id,
            analysis_run_id=run_id,
            insight_text=insight_text,
            feedback_type=feedback_type,
            comments=comments,
            timestamp=datetime.utcnow()
        )
        db.add(fb)
        db.commit()
    
    def get_positive_examples(self, db: Session, user_id: int, limit: int = 3) -> List[str]:
        """
        Retrieves top-rated advice to use as few-shot examples (RAG).
        """
        positive_feedback = db.query(InsightFeedback).filter(
            InsightFeedback.user_id == user_id,
            InsightFeedback.feedback_type == "THUMBS_UP"
        ).order_by(InsightFeedback.timestamp.desc()).limit(limit).all()
        
        return [fb.insight_text for fb in positive_feedback]

memory_service = MemoryService()
