from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid

router = APIRouter(prefix="/field-reports", tags=["field-reports"])

class FieldReport(BaseModel):
    id: str
    timestamp: str
    lat: float
    lon: float
    zone_id: Optional[str] = None
    category: str
    severity: str
    description: str
    reporter: str
    sync_status: str

# In-memory storage for demo acknowledgment
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
