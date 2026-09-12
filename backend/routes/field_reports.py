from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

router = APIRouter(prefix="/field-reports", tags=["field-reports"])

class FieldReport(BaseModel):
    id: str
    timestamp: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    zone_id: Optional[str] = None
    category: str
    severity: str
    description: str
    reporter: Optional[str] = ""
    photo_base64: Optional[str] = Field(default=None, max_length=2_000_000)
    photo_status: Optional[str] = None
    sync_status: str

    @validator("category")
    def validate_category(cls, v):
        allowed = ["landslide", "road_blockage", "cracks_slope_movement", "slope_crack", "debris", "flooding", "other"]
        if v not in allowed:
            raise ValueError(f"Category must be one of {allowed}")
        return v
    
    @validator("severity")
    def validate_severity(cls, v):
        allowed = ["low", "moderate", "high"]
        if v.lower() not in allowed:
            # Fallback mapping
            if v.lower() == "critical":
                return "high"
            raise ValueError(f"Severity must be one of {allowed}")
        return v.lower()

# In-memory prototype/demo acknowledgement storage
# Note: Non-persistent on serverless deployment. Not intended for permanent cloud storage.
demo_reports: Dict[str, FieldReport] = {}

@router.post("", response_model=FieldReport)
def submit_field_report(report: FieldReport):
    # Ensure ID is present, though PWA should generate it
    if not report.id:
        report.id = str(uuid.uuid4())
    # Mark as synced with backend
    report.sync_status = "SYNCED"
    
    demo_reports[report.id] = report
    return report

@router.get("", response_model=List[FieldReport])
def list_field_reports():
    return list(demo_reports.values())

@router.get("/{report_id}", response_model=FieldReport)
def get_field_report(report_id: str):
    if report_id not in demo_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    return demo_reports[report_id]
