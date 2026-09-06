from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uuid
from services.sms import get_sms_provider

router = APIRouter(prefix="/alerts", tags=["alerts"])

class Alert(BaseModel):
    alert_id: str
    zone_id: str
    created_at: str
    category: str
    severity: str
    risk_horizon: str
    risk_category: str
    priority_category: str
    rationale: str
    delivery_channels: List[str]
    delivery_status: str

# In-memory prototype history
# Note: Non-persistent across serverless restarts. Not intended for permanent cloud storage.
demo_alerts: List[Alert] = []

@router.get("", response_model=List[Alert])
def list_alerts():
    return demo_alerts

@router.post("/test", response_model=Alert)
def test_alert(zone_id: str = "C03"):
    alert = Alert(
        alert_id=str(uuid.uuid4()),
        zone_id=zone_id,
        created_at=datetime.utcnow().isoformat() + "Z",
        category="landslide_warning",
        severity="VERY_HIGH",
        risk_horizon="+24h",
        risk_category="VERY_HIGH",
        priority_category="VERY_HIGH",
        rationale="Elevated rainfall + steep terrain.",
        delivery_channels=["sms", "browser"],
        delivery_status="DEMO_PREVIEW"
    )
    demo_alerts.insert(0, alert)
    
    # Send SMS preview
    sms_provider = get_sms_provider()
    message = f"TerraSense NER Alert\nZone {zone_id}\nPriority: VERY HIGH\nOutlook: +24h\n{alert.rationale}"
    status = sms_provider.send_sms("+919876543210", message)
    alert.delivery_status = status
    
    return alert
