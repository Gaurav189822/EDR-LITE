from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class SeverityLevel(str, Enum):
    """Severity levels for alerts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertBase(BaseModel):
    """Base model for alerts"""
    process_id: int = Field(..., description="ID of the related process")
    rule_triggered: str = Field(..., description="Name of the rule that triggered")
    severity: SeverityLevel = Field(..., description="Alert severity level")
    description: str = Field(..., description="Human-readable alert description")
    risk_score: int = Field(default=0, ge=0, le=100, description="Calculated risk score")


class AlertCreate(AlertBase):
    """Model for creating a new alert"""
    details: Optional[Dict[str, Any]] = Field(None, description="Additional alert details")


class Alert(AlertBase):
    """Full alert model with database ID"""
    id: int
    timestamp: datetime
    acknowledged: bool = False
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """Response model for alert endpoints"""
    total: int
    alerts: list[Alert]
    severity_counts: Dict[str, int]


class AlertStats(BaseModel):
    """Statistics for alerts dashboard"""
    total_alerts: int
    high_severity: int
    medium_severity: int
    low_severity: int
    critical_severity: int
    recent_alerts: list[Alert]
    alerts_by_hour: Dict[str, int]