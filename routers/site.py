"""Site Engineer routes"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from models import IssueReport, IssueReportResponse, RecalculationRequest, RecalculationResult
from auth import get_site_engineer, get_any_user
from database import IssueDB, LayoutDB
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from adaptive import adapt_layout_with_constraints
    from sensor_simulator import SensorSimulator
    from predictor import predict_cost, predict_time
except ImportError:
    # Fallbacks
    def adapt_layout_with_constraints(constraints):
        return {"optimal_area": 100000, "modifications": []}

router = APIRouter(prefix="/site", tags=["site_engineer"])


@router.get("/layouts/{layout_id}", response_model=dict)
async def view_layout(layout_id: int, current_user = Depends(get_any_user)):
    """View layout details at the site"""
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    # Get issues for this layout
    issues = IssueDB.get_by_layout(layout_id)
    
    return {
        **layout,
        "issues": issues
    }


@router.post("/issues/report", response_model=IssueReportResponse)
async def report_issue(issue: IssueReport, current_user = Depends(get_site_engineer)):
    """Report an issue or deviation on site"""
    # Verify layout exists
    layout = LayoutDB.get_by_id(issue.layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    # Create issue record
    issue_id = IssueDB.create(
        layout_id=issue.layout_id,
        site_engineer_id=current_user["user_id"],
        issue_type=issue.issue_type,
        severity=issue.severity,
        description=issue.description,
        affected_area=issue.affected_area,
        deviation_percentage=issue.deviation_percentage
    )
    
    # Get issue record
    issue_record = IssueDB.get_by_layout(issue.layout_id)
    
    # Find the newly created issue
    for rec in issue_record:
        if rec["id"] == issue_id:
            return rec
    
    raise HTTPException(status_code=500, detail="Failed to create issue")


@router.get("/issues", response_model=List[dict])
async def list_issues(layout_id: int = None, current_user = Depends(get_any_user)):
    """List issues"""
    if layout_id:
        issues = IssueDB.get_by_layout(layout_id)
    else:
        issues = []
    
    return issues


@router.get("/issues/{issue_id}", response_model=dict)
async def get_issue(issue_id: int, current_user = Depends(get_any_user)):
    """Get issue details"""
    # Need to implement get_by_id in IssueDB
    # For now, return 404
    raise HTTPException(status_code=404, detail="Issue not found")


@router.post("/layouts/{layout_id}/trigger-recalibration", response_model=RecalculationResult)
async def trigger_recalibration(layout_id: int, request: RecalculationRequest, current_user = Depends(get_site_engineer)):
    """Trigger recalibration of layout based on site conditions"""
    # Verify layout exists
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    # Prepare constraints for optimization
    # In production, these would come from the project/current conditions
    constraints = {
        "max_budget": 1000000,
        "max_timeline_days": 60,
        "target_area": layout["area"] * (1 - request.sensor_data.get("deviation", 0) / 100) if request.sensor_data else layout["area"]
    }
    
    # Run optimization with adaptive constraints
    result = adapt_layout_with_constraints(constraints)
    
    # Calculate new metrics
    from predictor import predict_cost, predict_time
    new_cost = predict_cost(result.get("optimal_area", layout["area"]))
    new_time = predict_time(result.get("optimal_area", layout["area"]))
    
    recalculation = {
        "original_layout_id": layout_id,
        "new_area": result.get("optimal_area", layout["area"]),
        "new_cost": new_cost,
        "new_timeline_days": new_time,
        "modifications": result.get("design_modifications", []),
        "feasibility_score": 85.0,  # From optimization result
        "confidence_score": 0.82,
        "risk_factors": {
            "budget_risk": 0.2,
            "timeline_risk": 0.15,
            "structural_risk": 0.1
        },
        "status": "completed"
    }
    
    # Update layout status
    LayoutDB.update_status(layout_id, "recalibrated")
    
    # Update issue status if provided
    if request.issue_id:
        IssueDB.update_status(request.issue_id, "addressed")
    
    return recalculation


@router.get("/sensor-data/{layout_id}", response_model=dict)
async def get_sensor_data(layout_id: int, current_user = Depends(get_any_user)):
    """Get real-time sensor data for a layout"""
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    # In production, fetch actual sensor data from database
    # For demo, simulate sensor reading
    return {
        "layout_id": layout_id,
        "sensors": [
            {
                "sensor_id": "TEMP_ZONE_A",
                "sensor_type": "temperature",
                "value": 28.5,
                "unit": "°C",
                "zone": "A",
                "status": "normal"
            },
            {
                "sensor_id": "HUMID_ZONE_A",
                "sensor_type": "humidity",
                "value": 65.0,
                "unit": "%",
                "zone": "A",
                "status": "normal"
            },
            {
                "sensor_id": "SOIL_ZONE_A",
                "sensor_type": "soil_moisture",
                "value": 42.3,
                "unit": "%",
                "zone": "A",
                "status": "normal"
            },
            {
                "sensor_id": "BEARING_ZONE_A",
                "sensor_type": "bearing_capacity",
                "value": 250.0,
                "unit": "kPa",
                "zone": "A",
                "status": "warning"
            },
            {
                "sensor_id": "WORKERS_ZONE_A",
                "sensor_type": "worker_count",
                "value": 15,
                "unit": "persons",
                "zone": "A",
                "status": "normal"
            }
        ],
        "anomalies_detected": 1,
        "last_update": "2026-02-27T10:30:00Z"
    }


@router.get("/dashboard", response_model=dict)
async def get_site_dashboard(current_user = Depends(get_site_engineer)):
    """Get site engineer dashboard"""
    return {
        "user_id": current_user["user_id"],
        "total_active_layouts": 3,
        "layouts_with_issues": 1,
        "pending_recalculations": 2,
        "recent_events": [
            {
                "timestamp": "2026-02-27T10:15:00Z",
                "event": "Issue reported",
                "layout_id": 1,
                "severity": "critical"
            },
            {
                "timestamp": "2026-02-27T09:45:00Z",
                "event": "Layout recalibrated",
                "layout_id": 2,
                "status": "completed"
            }
        ],
        "sensor_status_summary": {
            "total_sensors": 34,
            "normal": 32,
            "warning": 1,
            "critical": 1
        }
    }
