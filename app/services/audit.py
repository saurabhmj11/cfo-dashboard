"""
Enterprise Audit Service v2.0
Comprehensive audit logging with structured data, categories, and query capabilities.
"""
from sqlalchemy.orm import Session
from app.models.db_models import AuditLog
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import json
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
audit_logger = logging.getLogger("audit")


class AuditCategory(str, Enum):
    """Categories of audit events."""
    AUTH = "AUTH"              # Login, logout, password change
    DATA = "DATA"              # Data access, modification
    ADMIN = "ADMIN"            # Admin actions
    SYSTEM = "SYSTEM"          # System events
    SECURITY = "SECURITY"      # Security events
    ANALYSIS = "ANALYSIS"      # AI analysis runs
    INTEGRATION = "INTEGRATION" # External integrations


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEvent:
    """Structured audit event."""
    
    def __init__(
        self,
        action: str,
        user_id: Optional[int],
        category: AuditCategory,
        severity: AuditSeverity = AuditSeverity.INFO,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        self.action = action
        self.user_id = user_id
        self.category = category
        self.severity = severity
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details
        self.metadata = metadata or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "user_id": self.user_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat()
        }


class AuditService:
    """
    Enterprise Audit Service.
    Records all critical system actions for compliance, security, and debugging.
    
    Features:
    - Structured event logging
    - Categorized events
    - Severity levels
    - Query capabilities
    - File-based fallback logging
    """
    
    def __init__(self):
        self._in_memory_logs: List[Dict] = []  # Fallback if DB fails
        self._max_memory_logs = 1000
    
    def log(
        self,
        db: Optional[Session],
        event: AuditEvent
    ) -> bool:
        """
        Log an audit event.
        
        Args:
            db: Database session (optional, falls back to memory/file)
            event: The audit event to log
        
        Returns:
            True if logged successfully
        """
        try:
            # Always log to structured logger
            log_data = event.to_dict()
            audit_logger.info(
                f"[{event.category.value}] {event.action}",
                extra={"audit_data": log_data}
            )
            
            # Log to database if available
            if db:
                audit_log = AuditLog(
                    user_id=event.user_id,
                    action=f"[{event.category.value}] {event.action}",
                    resource_id=event.resource_id,
                    details=json.dumps({
                        "severity": event.severity.value,
                        "resource_type": event.resource_type,
                        "description": event.details,
                        "metadata": event.metadata,
                        "ip": event.ip_address
                    }),
                    timestamp=event.timestamp
                )
                db.add(audit_log)
                db.commit()
            else:
                # Fallback to in-memory
                self._in_memory_logs.append(log_data)
                if len(self._in_memory_logs) > self._max_memory_logs:
                    self._in_memory_logs = self._in_memory_logs[-self._max_memory_logs:]
            
            return True
            
        except Exception as e:
            # Critical: Audit failures should never crash the system
            audit_logger.error(f"AUDIT FAILURE: {e}", extra={"event": event.action})
            return False
    
    # Convenience methods for common audit events
    
    def log_action(
        self, 
        db: Session, 
        user_id: int, 
        action: str, 
        resource_id: str = None, 
        details: str = ""
    ):
        """Legacy method for backward compatibility."""
        event = AuditEvent(
            action=action,
            user_id=user_id,
            category=AuditCategory.DATA,
            resource_id=resource_id,
            details=details
        )
        return self.log(db, event)
    
    def log_auth_event(
        self,
        db: Optional[Session],
        action: str,
        user_id: Optional[int],
        success: bool,
        ip_address: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log authentication events."""
        event = AuditEvent(
            action=action,
            user_id=user_id,
            category=AuditCategory.AUTH,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            details=details,
            ip_address=ip_address,
            metadata={"success": success}
        )
        return self.log(db, event)
    
    def log_security_event(
        self,
        db: Optional[Session],
        action: str,
        severity: AuditSeverity,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        details: Optional[str] = None
    ):
        """Log security-related events."""
        event = AuditEvent(
            action=action,
            user_id=user_id,
            category=AuditCategory.SECURITY,
            severity=severity,
            details=details,
            ip_address=ip_address
        )
        return self.log(db, event)
    
    def log_data_access(
        self,
        db: Session,
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str = "ACCESS"
    ):
        """Log data access events."""
        event = AuditEvent(
            action=action,
            user_id=user_id,
            category=AuditCategory.DATA,
            resource_type=resource_type,
            resource_id=resource_id
        )
        return self.log(db, event)
    
    def log_analysis_run(
        self,
        db: Session,
        user_id: int,
        analysis_type: str,
        dataset_id: Optional[int] = None,
        result_summary: Optional[str] = None
    ):
        """Log AI analysis runs."""
        event = AuditEvent(
            action=f"ANALYSIS_RUN:{analysis_type}",
            user_id=user_id,
            category=AuditCategory.ANALYSIS,
            resource_type="dataset",
            resource_id=str(dataset_id) if dataset_id else None,
            details=result_summary
        )
        return self.log(db, event)
    
    # Query methods
    
    def get_user_activity(
        self,
        db: Session,
        user_id: int,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """Get recent activity for a user."""
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)
        
        if since:
            query = query.filter(AuditLog.timestamp >= since)
        
        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "resource_id": log.resource_id,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    
    def get_security_events(
        self,
        db: Session,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """Get recent security events."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        logs = db.query(AuditLog).filter(
            AuditLog.timestamp >= since,
            AuditLog.action.like("[SECURITY]%")
        ).order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "user_id": log.user_id,
                "details": log.details,
                "timestamp": log.timestamp.isoformat()
            }
            for log in logs
        ]
    
    def get_in_memory_logs(self) -> List[Dict]:
        """Get logs stored in memory (fallback)."""
        return self._in_memory_logs.copy()


# Singleton instance
audit_service = AuditService()
