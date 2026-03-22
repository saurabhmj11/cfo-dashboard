from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date

class FinancialRecord(BaseModel):
    date: date
    revenue: float = Field(..., ge=0)
    expenses: float = Field(..., ge=0)
    category: Optional[str] = "Uncategorized"

    @field_validator('revenue', 'expenses', mode='before')
    def parse_float(cls, v):
        if isinstance(v, str):
            return float(v.replace(',', '').replace('$', ''))
        return v

class MonthlyMetric(BaseModel):
    month: str
    revenue: float
    expenses: float
    net_profit: float
    margin_percent: float
    growth_mom: Optional[float] = 0.0

class Anomaly(BaseModel):
    date: str
    metric: str  # "revenue" or "expenses"
    value: float
    deviation_percent: float
    severity: str # "High", "Medium", "Low"
    description: str

class FinancialAnalysisResult(BaseModel):
    summary_revenue: float
    summary_expenses: float
    summary_profit: float
    avg_margin: float
    monthly_data: List[MonthlyMetric]
    anomalies: List[Anomaly]
    confidence_score: float = 1.0

# Phase 2: The "Truth" Contract
class AnalysisPayload(BaseModel):
    """
    The immutable source of truth for Agents.
    Agents READ this. They do not CALCULATE this.
    """
    kpis: Dict[str, float] = Field(..., description="Deterministically calculated totals")
    trends: Dict[str, Any] = Field(..., description="Growth rates and month-over-month changes")
    anomalies: List[Anomaly] = Field(default_factory=list, description="Statistically verified outliers")
    confidence_score: float = Field(default=1.0, description="Trusted Score (0.0 - 1.0)")
    data_quality_issues: List[str] = Field(default_factory=list, description="Reasons for confidence penalty") 
    # Forecasts will be appended here after Oracle runs, but Detective reads KPIs/Trends


# Phase 2: Agent Output Schemas

class Observation(BaseModel):
    metric: str
    trend: str # "Growing", "Declining", "Stable", "Anomaly"
    confidence: float # 0.0 to 1.0
    detail: str

class DetectiveReport(BaseModel):
    summary: str
    observations: List[Observation]
    anomalies_detected: int

class ScenarioForecast(BaseModel):
    scenario_name: str # "Conservative", "Neutral", "Aggressive"
    predicted_revenue: List[float]
    confidence_band_upper: List[float]
    confidence_band_lower: List[float]
    assumptions: Dict[str, Any]

class ForecastReport(BaseModel):
    scenarios: List[ScenarioForecast]
    best_case_total: float
    worst_case_total: float
    forecast_data: List[Dict[str, Any]] = []
    model_confidence: float = 0.0

class ImpactPrediction(BaseModel):
    input_action: str
    predicted_metric: str
    predicted_impact_value: float
    confidence_score: float
    explanation: str

class AdviceCard(BaseModel):
    decision: str
    reason: str # "Root Cause"
    impact: str # Text summary
    risk: str 
    confidence: float
    # Phase 2 additions
    root_cause: Optional[str] = None 
    suggested_action: Optional[str] = None
    impact_value: Optional[float] = None # Numeric impact for sorting
    
class AdvisorReport(BaseModel):
    strategic_advice: List[AdviceCard]

class AdvisorContext(BaseModel):
    """
    Context for the Advisor to "remember" user preferences.
    """
    rejected_topics: List[str] = Field(default_factory=list, description="List of 'decision' strings previously rejected")
    positive_examples: List[str] = Field(default_factory=list, description="Top rated advice from the past (One-Shot Learning)")
    preferred_strategy: str = "Balanced" # Placeholder for future "Persona" setting

# Phase 3: Tenant Schemas
class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    plan_type: Optional[str] = "FREE"

class Tenant(TenantBase):
    id: int
    plan_type: str
    
    class Config:
        from_attributes = True

# Phase 3: Auth Schemas

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    tenant_id: Optional[int] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True

