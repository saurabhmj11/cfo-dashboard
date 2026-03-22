from sqlalchemy.orm import Session
from app.models.db_models import PendingAction, User
from typing import Dict, List, Optional
import json

class ActionService:
    """
    The Action Desk Engine.
    Manages the lifecycle of autonomous actions: Draft -> Approve -> Execute.
    """
    
    def draft_action(self, db: Session, user_id: int, type: str, title: str, description: str, payload: Dict) -> PendingAction:
        """
        Creates a new action in PENDING state.
        This is what the Agents call when they want to 'do' something.
        """
        action = PendingAction(
            user_id=user_id,
            action_type=type,
            title=title,
            description=description,
            payload=payload,
            status="PENDING"
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return action

    def get_pending_actions(self, db: Session, user_id: int) -> List[PendingAction]:
        return db.query(PendingAction).filter(
            PendingAction.user_id == user_id,
            PendingAction.status == "PENDING"
        ).order_by(PendingAction.created_at.desc()).all()

    def execute_action(self, db: Session, user_id: int, action_id: int) -> Dict:
        """
        Safely executes an approved action.
        """
        action = db.query(PendingAction).filter(
            PendingAction.id == action_id,
            PendingAction.user_id == user_id
        ).first()
        
        if not action:
            return {"status": "error", "message": "Action not found"}
        
        if action.status == "EXECUTED":
             return {"status": "error", "message": "Already executed"}
             
        # EXECUTION LOGIC (Stubs for now)
        try:
            result_log = ""
            if action.action_type == "EMAIL":
                # Stub: send_email(action.payload['to'], ...)
                result_log = f"Sent email to {action.payload.get('to')} via SMTP Relay."
            elif action.action_type == "JIRA":
                # Stub: jira.create_issue(...)
                result_log = f"Created Jira Ticket PROJ-{action.payload.get('priority')}."
            elif action.action_type == "SLACK":
                result_log = f"Posted to #{action.payload.get('channel')}."
            else:
                result_log = "Unknown action type executed."
            
            action.status = "EXECUTED"
            action.execution_log = result_log
            db.commit()
            
            return {"status": "success", "log": result_log}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def reject_action(self, db: Session, user_id: int, action_id: int):
        action = db.query(PendingAction).filter(
            PendingAction.id == action_id,
            PendingAction.user_id == user_id
        ).first()
        if action:
            action.status = "REJECTED"
            db.commit()

action_service = ActionService()
