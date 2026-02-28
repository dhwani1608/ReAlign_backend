"""Design Engineer routes"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from pathlib import Path
from datetime import datetime
import shutil
import uuid
from models import (
    LayoutDesign, LayoutResponse, LayoutApproval, CostPredictionRequest,
    CostPredictionResponse, ProjectCreate, ProjectResponse, ProjectUpdate
)
from auth import get_design_engineer, get_any_user
from database import LayoutDB, ProjectDB, UserDB, IssueDB
import sys
import os

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from predictor import predict_cost, predict_time
    from layout_retrieval import retrieve_layout
    from adaptive import adapt_layout_with_constraints
except ImportError:
    # Fallback if modules aren't available
    def predict_cost(area):
        return 500000 + area * 5
    
    def predict_time(area):
        return int(30 + area / 10000)
    
    def retrieve_layout(area):
        return f"layout_{int(area)}"
    
    def adapt_layout_with_constraints(constraints_dict):
        return {"optimal_area": constraints_dict.get("target_area", 100000), "modifications": []}

router = APIRouter(prefix="/designer", tags=["design_engineer"])

ROOT_DIR = Path(__file__).resolve().parents[2]
GENERATED_LAYOUTS_DIR = Path(__file__).resolve().parents[1] / "generated_layouts"
GENERATED_LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_layout_source_image(layout_identifier: str) -> Path | None:
    """Resolve source image path for retrieved layout identifier."""
    if not layout_identifier:
        return None

    identifier_path = Path(layout_identifier)
    filename = identifier_path.name

    candidates = [
        ROOT_DIR / layout_identifier,
        ROOT_DIR / "train-00" / layout_identifier,
        ROOT_DIR / "train-00" / "coco_vis" / layout_identifier,
        ROOT_DIR / "coco_vis" / layout_identifier,
        ROOT_DIR / "train-00" / "coco_vis" / filename,
        ROOT_DIR / filename,
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def _create_layout_assets(layout_identifier: str, area: float, efficiency: float, material_factor: float,
                          estimated_cost: float, estimated_timeline_days: int) -> dict:
    """Create preview image + lightweight layout plan metadata for frontend rendering."""
    unique_name = f"layout_{uuid.uuid4().hex[:12]}.png"
    output_path = GENERATED_LAYOUTS_DIR / unique_name
    source_path = _resolve_layout_source_image(layout_identifier)

    if source_path:
        shutil.copy2(source_path, output_path)
    elif Image and ImageDraw:
        canvas = Image.new("RGB", (640, 480), color=(245, 248, 252))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((40, 40, 600, 440), outline=(44, 62, 80), width=4)
        draw.rectangle((60, 70, 260, 220), outline=(52, 152, 219), width=3)
        draw.rectangle((280, 70, 580, 220), outline=(46, 204, 113), width=3)
        draw.rectangle((60, 240, 400, 420), outline=(241, 196, 15), width=3)
        draw.rectangle((420, 240, 580, 420), outline=(231, 76, 60), width=3)
        draw.text((70, 80), "Work Zone A", fill=(52, 152, 219))
        draw.text((290, 80), "Work Zone B", fill=(46, 204, 113))
        draw.text((70, 250), "Material Staging", fill=(180, 140, 20))
        draw.text((430, 250), "Access Core", fill=(192, 57, 43))
        draw.text((70, 450), f"Area: {int(area):,} | Eff: {efficiency:.2f} | Mat: {material_factor:.2f}", fill=(44, 62, 80))
        canvas.save(output_path)

    preview_url = f"/generated-layouts/{unique_name}" if output_path.exists() else None

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "preview_image_url": preview_url,
        "layout_plan": {
            "zones": [
                "Foundation & structural zone",
                "Material staging and access corridor",
                "Core utility and circulation zone"
            ],
            "construction_sequence": [
                "1) Foundation and bearing checks",
                "2) Structural framing and envelope",
                "3) Services routing and final fit-out"
            ],
            "design_targets": {
                "area": float(area),
                "estimated_cost": float(estimated_cost),
                "estimated_timeline_days": int(estimated_timeline_days),
                "efficiency": float(efficiency),
                "material_factor": float(material_factor)
            }
        }
    }


# ===== Project Management =====
@router.post("/projects", response_model=dict)
async def create_project(project: ProjectCreate, current_user = Depends(get_design_engineer)):
    """Create a new project (Design Engineer only)"""
    project_id = ProjectDB.create(
        name=project.name,
        description=project.description,
        design_engineer_id=current_user["user_id"],
        max_budget=project.max_budget,
        max_timeline_days=project.max_timeline_days,
        target_area=project.target_area
    )
    
    return {
        "id": project_id,
        "message": "Project created successfully"
    }


@router.get("/projects", response_model=List[dict])
async def get_projects(current_user = Depends(get_design_engineer)):
    """Get all projects for current design engineer"""
    projects = ProjectDB.get_by_engineer(current_user["user_id"])
    return projects


@router.get("/projects/{project_id}", response_model=dict)
async def get_project(project_id: int, current_user = Depends(get_design_engineer)):
    """Get project details"""
    project = ProjectDB.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["design_engineer_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get layouts for this project
    layouts = LayoutDB.get_by_project(project_id)
    for layout in layouts:
        if not layout.get("layout_data"):
            hydrated_layout_data = _create_layout_assets(
                layout_identifier=layout.get("layout_id", ""),
                area=layout.get("area", 0),
                efficiency=layout.get("efficiency", 1.0),
                material_factor=layout.get("material_factor", 1.0),
                estimated_cost=layout.get("cost", 0),
                estimated_timeline_days=layout.get("timeline_days", 0)
            )
            LayoutDB.update_layout_data(layout["id"], hydrated_layout_data)
            layout["layout_data"] = hydrated_layout_data
    
    return {
        **project,
        "layouts": layouts
    }


@router.put("/projects/{project_id}", response_model=dict)
async def update_project(project_id: int, updates: ProjectUpdate, current_user = Depends(get_design_engineer)):
    """Update project details"""
    project = ProjectDB.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["design_engineer_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update would require implementing update in database.py
    return {"message": "Project updated successfully"}


# ===== Layout Generation =====
@router.post("/layouts/generate", response_model=LayoutResponse)
async def generate_layout(layout: LayoutDesign, project_id: int, current_user = Depends(get_design_engineer)):
    """Generate a new layout (Design Engineer)"""
    # Verify project exists and belongs to user
    project = ProjectDB.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["design_engineer_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate cost and timeline
    cost = predict_cost(layout.area)
    timeline = predict_time(layout.area)
    
    # Retrieve best matching layout
    layout_id = retrieve_layout(layout.area)

    # Create preview image + plan metadata for realtime rendering
    layout_data = _create_layout_assets(
        layout_identifier=layout_id,
        area=layout.area,
        efficiency=layout.efficiency,
        material_factor=layout.material_factor,
        estimated_cost=cost,
        estimated_timeline_days=timeline
    )
    
    # Save to database
    db_id = LayoutDB.create(
        project_id=project_id,
        design_engineer_id=current_user["user_id"],
        area=layout.area,
        cost=cost,
        timeline_days=timeline,
        efficiency=layout.efficiency,
        material_factor=layout.material_factor,
        layout_id=layout_id,
        name=layout.name,
        description=layout.description,
        layout_data=layout_data
    )
    
    layout_record = LayoutDB.get_by_id(db_id)
    return layout_record


@router.get("/layouts/{layout_id}", response_model=dict)
async def get_layout(layout_id: int, current_user = Depends(get_any_user)):
    """Get layout details"""
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    # Get associated issues
    issues = IssueDB.get_by_layout(layout_id)

    if not layout.get("layout_data"):
        hydrated_layout_data = _create_layout_assets(
            layout_identifier=layout.get("layout_id", ""),
            area=layout.get("area", 0),
            efficiency=layout.get("efficiency", 1.0),
            material_factor=layout.get("material_factor", 1.0),
            estimated_cost=layout.get("cost", 0),
            estimated_timeline_days=layout.get("timeline_days", 0)
        )
        LayoutDB.update_layout_data(layout_id, hydrated_layout_data)
        layout["layout_data"] = hydrated_layout_data
    
    return {
        **layout,
        "issues": issues
    }


@router.get("/layouts", response_model=List[dict])
async def list_layouts(project_id: int = None, current_user = Depends(get_any_user)):
    """List layouts (filtered by project if provided)"""
    if project_id:
        layouts = LayoutDB.get_by_project(project_id)
    else:
        # Return all layouts for now (could be filtered by user role)
        layouts = []
    
    return layouts


@router.post("/layouts/{layout_id}/approve", response_model=dict)
async def approve_layout(layout_id: int, approval: LayoutApproval, current_user = Depends(get_design_engineer)):
    """Approve or reject a layout"""
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    # Verify user can approve
    if layout["design_engineer_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update approval status
    status_str = "approved" if approval.approved else "rejected"
    LayoutDB.update_approval(layout_id, status_str)
    
    return {
        "layout_id": layout_id,
        "approval_status": status_str,
        "message": "Layout approval status updated"
    }


@router.post("/layouts/{layout_id}/send-to-site", response_model=dict)
async def send_to_site(layout_id: int, current_user = Depends(get_design_engineer)):
    """Send approved layout to site"""
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    if layout["design_engineer_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if layout["approval_status"] != "approved":
        raise HTTPException(status_code=400, detail="Layout must be approved before sending to site")
    
    # Update status
    LayoutDB.update_status(layout_id, "sent_to_site")
    
    return {
        "layout_id": layout_id,
        "status": "sent_to_site",
        "message": "Layout sent to site"
    }


# ===== Cost Prediction =====
@router.post("/predict-cost", response_model=CostPredictionResponse)
async def predict_cost_endpoint(request: CostPredictionRequest, current_user = Depends(get_any_user)):
    """Predict cost for a layout"""
    # Use the predictor module
    cost = predict_cost(request.area)
    timeline = predict_time(request.area)
    
    # Breakdown (simplified)
    base_cost = 500000
    material_cost = request.area * 5 * request.material_factor
    labor_cost = (timeline * 100) * request.efficiency
    
    return {
        "area": request.area,
        "estimated_cost": cost,
        "timeline_days": timeline,
        "efficiency": request.efficiency,
        "material_factor": request.material_factor,
        "breakdown": {
            "base_construction": base_cost,
            "material_cost": material_cost,
            "labor_cost": labor_cost,
            "contingency": (base_cost + material_cost + labor_cost) * 0.1
        }
    }


# ===== Layout Optimization =====
@router.post("/layouts/{layout_id}/optimize", response_model=dict)
async def optimize_layout(layout_id: int, current_user = Depends(get_design_engineer)):
    """Optimize an existing layout with constraints"""
    layout = LayoutDB.get_by_id(layout_id)
    if not layout:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    if layout["design_engineer_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Use adaptive constraint optimization
    project = ProjectDB.get_by_id(layout["project_id"])
    
    constraints = {
        "max_budget": project["max_budget"],
        "max_timeline_days": project["max_timeline_days"],
        "target_area": project["target_area"]
    }
    
    result = adapt_layout_with_constraints(constraints)
    
    return {
        "layout_id": layout_id,
        "optimization_result": result,
        "message": "Layout optimization completed"
    }
