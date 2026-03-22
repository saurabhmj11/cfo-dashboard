from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    plan_type = Column(String, default="FREE") # "FREE", "PRO", "ENTERPRISE"
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    datasets = relationship("Dataset", back_populates="tenant")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True) # Nullable for legacy users initially
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="CFO")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    file_path = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    
    # Validation Metadata
    row_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    is_golden = Column(Integer, default=0) # 1 if validated successfully

    transactions = relationship("Transaction", back_populates="dataset")
    aggregates = relationship("MonthlyAggregate", back_populates="dataset")
    tenant = relationship("Tenant", back_populates="datasets")

# --- Layer 2: The Golden Data ---
class Transaction(Base):
    """
    Granular, Validated Financial Data.
    Source of Truth for all downstream analytics.
    """
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    
    txn_date = Column(Date, nullable=False, index=True)
    revenue = Column(Float, default=0.0)
    expenses = Column(Float, default=0.0)
    category = Column(String, index=True)
    
    dataset = relationship("Dataset", back_populates="transactions")

class MonthlyAggregate(Base):
    """
    Pre-computed Aggregates (Materialized View equivalent).
    Used for fast dashboard loading (Layer 3 output).
    """
    __tablename__ = "monthly_aggregates"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    
    month_key = Column(String, index=True) # "2023-01"
    total_revenue = Column(Float)
    total_expenses = Column(Float)
    gross_profit = Column(Float)
    margin_pct = Column(Float)
    
    # Audit trail
    computed_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="aggregates")

# --- Layer 7: Scale & Control ---
class AuditLog(Base):
    """
    Enterprise Audit Trail.
    Tracks 'Who did What and When'.
    Immutable record of system actions.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String) # "UPLOAD", "ANALYSIS", "SIMULATION", "FEEDBACK"
    resource_id = Column(String, nullable=True) # e.g., DatasetID or RunID
    details = Column(String) # JSON or Text summary
    ip_address = Column(String, nullable=True)

class InsightFeedback(Base):
    """
    Human-in-the-Loop Feedback.
    Captures CFO approval/rejection of AI Advice.
    Used to fine-tune the 'Advisor' agent in future iterations.
    """
    __tablename__ = "insight_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id"))
    
    insight_text = Column(String) # The advice given
    feedback_type = Column(String) # "APPROVE", "REJECT", "EDIT"
    comments = Column(String, nullable=True)

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id = Column(Integer, primary_key=True, index=True)
    run_date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    
    # Store JSON results
    metrics_result = Column(JSON)
    forecast_result = Column(JSON)
    advisor_result = Column(JSON)

    feedback = relationship("InsightFeedback", backref="run")

class PendingAction(Base):
    """
    Phase 6: The Action Desk.
    Stores draft actions waiting for human approval.
    Safety First: No external call is made until status='EXECUTED'.
    """
    __tablename__ = "pending_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    action_type = Column(String) # "EMAIL", "JIRA", "SLACK"
    status = Column(String, default="PENDING") # "PENDING", "APPROVED", "REJECTED", "EXECUTED"
    
    # Payload (The content of the action)
    title = Column(String) # E.g. "Email to AWS Support"
    description = Column(String)
    payload = Column(JSON) # { "to": "...", "body": "...", "subject": "..." }
    
    execution_log = Column(String, nullable=True) # Result of the API call
