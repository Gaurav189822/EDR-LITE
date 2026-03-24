"""
Alerts API Routes

REST API endpoints for alert management and retrieval.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AlertResponse, Alert, SeverityLevel

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertResponse)
async def get_alerts(
    limit: int = Query(100, ge=1, le=1000, description="Number of alerts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledged status"),
    session: AsyncSession = Depends(get_db)
):
    """
    Get alerts with optional filtering.
    
    - **limit**: Maximum number of alerts to return (1-1000)
    - **offset**: Pagination offset
    - **severity**: Filter by severity level (low, medium, high, critical)
    - **acknowledged**: Filter by acknowledged status
    """
    from database.database import db
    
    alerts = await db.get_alerts_async(
        session, 
        limit=limit, 
        offset=offset,
        severity=severity.value if severity else None,
        acknowledged=acknowledged
    )
    
    # Get total count for pagination
    severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for alert in alerts:
        if alert.severity in severity_counts:
            severity_counts[alert.severity] += 1
    
    return AlertResponse(
        total=len(alerts),
        alerts=[Alert.model_validate(alert) for alert in alerts],
        severity_counts=severity_counts
    )


@router.get("/stats")
async def get_alert_stats(session: AsyncSession = Depends(get_db)):
    """Get alert statistics for dashboard"""
    from database.database import db
    
    stats = db.get_alert_stats()
    return stats


@router.get("/recent")
async def get_recent_alerts(
    minutes: int = Query(60, ge=1, le=1440, description="Time window in minutes"),
    session: AsyncSession = Depends(get_db)
):
    """Get alerts from the last N minutes"""
    from database.database import db
    from sqlalchemy import select, desc
    from database.models import AlertModel
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    
    result = await session.execute(
        select(AlertModel)
        .where(AlertModel.timestamp >= cutoff)
        .order_by(desc(AlertModel.timestamp))
    )
    
    alerts = result.scalars().all()
    return [Alert.model_validate(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get a specific alert by ID"""
    from database.models import AlertModel
    
    alert = await session.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return Alert.model_validate(alert)


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Mark an alert as acknowledged"""
    from database.models import AlertModel
    
    alert = await session.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.acknowledged = True
    await session.commit()
    
    return {"status": "success", "message": f"Alert {alert_id} acknowledged"}


@router.post("/{alert_id}/unacknowledge")
async def unacknowledge_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Mark an alert as unacknowledged"""
    from database.models import AlertModel
    
    alert = await session.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.acknowledged = False
    await session.commit()
    
    return {"status": "success", "message": f"Alert {alert_id} unacknowledged"}


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete an alert"""
    from database.models import AlertModel
    
    alert = await session.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    await session.delete(alert)
    await session.commit()
    
    return {"status": "success", "message": f"Alert {alert_id} deleted"}


@router.post("/bulk/acknowledge")
async def bulk_acknowledge_alerts(
    alert_ids: List[int],
    session: AsyncSession = Depends(get_db)
):
    """Acknowledge multiple alerts at once"""
    from database.models import AlertModel
    from sqlalchemy import select
    
    result = await session.execute(
        select(AlertModel).where(AlertModel.id.in_(alert_ids))
    )
    alerts = result.scalars().all()
    
    for alert in alerts:
        alert.acknowledged = True
    
    await session.commit()
    
    return {
        "status": "success", 
        "message": f"Acknowledged {len(alerts)} alerts"
    }