"""Pydantic models for the application"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    DESIGN_ENGINEER = "design_engineer"
    SITE_ENGINEER = "site_engineer"
    ADMIN = "admin"


# === Authentication Models ===
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: UserRole


class UserLogin(BaseModel):
    email: str
    password: str
    
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# === Layout Models ===
class LayoutDesign(BaseModel):
    area: float = Field(..., gt=0)
    efficiency: float = Field(..., ge=0.5, le=1.5)
    material_factor: float = Field(..., ge=0.5, le=1.5)
    name: Optional[str] = None
    description: Optional[str] = None


class LayoutResponse(BaseModel):
    id: int
    design_engineer_id: int
    area: float
    cost: float
    timeline_days: int
    efficiency: float
    material_factor: float
    layout_id: str
    status: str
    approval_status: str
    created_at: datetime
    updated_at: datetime
    name: Optional[str] = None
    description: Optional[str] = None
    layout_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class LayoutApproval(BaseModel):
    layout_id: int
    approved: bool
    comments: Optional[str] = None


class LayoutUpdate(BaseModel):
    layout_id: int
    new_area: Optional[float] = None
    new_efficiency: Optional[float] = None
    status: Optional[str] = None


# === Issue/Problem Report Models ===
class IssueReport(BaseModel):
    layout_id: int
    issue_type: str  # "delay", "deviation", "resource_shortage", "safety_concern"
    severity: str  # "low", "medium", "critical"
    description: str
    affected_area: float
    deviation_percentage: float


class IssueReportResponse(BaseModel):
    id: int
    layout_id: int
    site_engineer_id: int
    issue_type: str
    severity: str
    description: str
    affected_area: float
    deviation_percentage: float
    status: str
    created_at: datetime
    recalculation_triggered: bool

    class Config:
        from_attributes = True


# === Sensor Data Models ===
class SensorReading(BaseModel):
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    zone: str
    timestamp: datetime


class SensorStatus(BaseModel):
    sensor_id: str
    sensor_type: str
    latest_value: float
    unit: str
    zone: str
    status: str  # "normal", "warning", "critical"
    anomaly_detected: bool
    last_reading_timestamp: datetime


# === Optimization & Recalibration Models ===
class RecalculationRequest(BaseModel):
    layout_id: int
    issue_id: Optional[int] = None
    trigger_reason: str
    sensor_data: Optional[Dict[str, Any]] = None


class RecalculationResult(BaseModel):
    original_layout_id: int
    new_area: float
    new_cost: float
    new_timeline_days: int
    modifications: List[str]
    feasibility_score: float
    risk_factors: Dict[str, float]
    confidence_score: float
    status: str


class CostPredictionRequest(BaseModel):
    area: float
    efficiency: Optional[float] = 1.0
    material_factor: Optional[float] = 1.0


class CostPredictionResponse(BaseModel):
    area: float
    estimated_cost: float
    timeline_days: int
    efficiency: float
    material_factor: float
    breakdown: Dict[str, float]


# === Project/Session Models ===
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_budget: float
    max_timeline_days: int
    target_area: float


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    design_engineer_id: int
    max_budget: float
    max_timeline_days: int
    target_area: float
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# === Dashboard/Analytics Models ===
class DashboardMetrics(BaseModel):
    total_layouts: int
    approved_layouts: int
    pending_approvals: int
    active_issues: int
    avg_cost: float
    avg_timeline: int
    avg_feasibility_score: float
    recent_recalculations: int


class LayoutHistory(BaseModel):
    id: int
    layout_id: int
    area: float
    cost: float
    timeline_days: int
    timestamp: datetime
    change_reason: Optional[str] = None


class ProjectStats(BaseModel):
    project_id: int
    total_layouts_generated: int
    total_layouts_approved: int
    total_issues_reported: int
    total_recalculations: int
    avg_confidence_score: float
    total_cost_variance: float
    timeline_variance_days: int


# === Message/Notification Models ===
class Message(BaseModel):
    id: Optional[int] = None
    from_user_id: int
    to_user_id: int
    layout_id: Optional[int] = None
    subject: str
    body: str
    read: bool = False
    created_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    layout_id: Optional[int] = None
    subject: str
    body: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
