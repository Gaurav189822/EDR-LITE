"""
Detection Engine API Routes

REST API endpoints for detection rules and engine management.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from detection import DetectionEngine, RuleManager
from models import DetectionRule, DetectionResult

router = APIRouter(prefix="/api/detection", tags=["detection"])

# Global detection engine instance
detection_engine: Optional[DetectionEngine] = None


def get_detection_engine() -> DetectionEngine:
    """Get or initialize detection engine"""
    global detection_engine
    if detection_engine is None:
        from database import Database
        db = Database()
        detection_engine = DetectionEngine(db)
    return detection_engine


class TestProcessRequest(BaseModel):
    """Request model for testing a process against rules"""
    process_name: str
    parent_name: str
    command_line: str
    process_id: int = 1234
    parent_process_id: int = 567


class RuleToggleRequest(BaseModel):
    """Request model for toggling rule state"""
    enabled: bool


@router.get("/rules")
async def get_rules(
    enabled_only: bool = Query(False, description="Return only enabled rules"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type")
):
    """Get all detection rules"""
    engine = get_detection_engine()
    
    if enabled_only:
        rules = engine.rule_manager.get_enabled_rules()
    else:
        rules = engine.rule_manager.rules
    
    if rule_type:
        from models import RuleType
        rules = [r for r in rules if r.rule_type.value == rule_type]
    
    # Convert to dict without compiled patterns
    rules_data = []
    for rule in rules:
        rule_dict = rule.dict(exclude={'_parent_pattern', '_child_pattern', '_cmd_pattern'})
        rule_dict['times_triggered'] = engine.rules_triggered.get(rule.id or '', 0)
        rules_data.append(rule_dict)
    
    return {
        "total": len(rules_data),
        "rules": rules_data
    }


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get a specific rule by ID"""
    engine = get_detection_engine()
    
    rule_details = engine.get_rule_details(rule_id)
    if not rule_details:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return rule_details


@router.post("/rules")
async def create_rule(rule: DetectionRule):
    """Create a new detection rule"""
    engine = get_detection_engine()
    
    success = engine.rule_manager.add_rule(rule)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to create rule")
    
    return {
        "status": "success",
        "message": f"Rule {rule.name} created",
        "rule_id": rule.id
    }


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, rule: DetectionRule):
    """Update an existing rule"""
    engine = get_detection_engine()
    
    existing = engine.rule_manager.get_rule(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Delete old rule
    engine.rule_manager.delete_rule(rule_id)
    
    # Create new rule with same ID
    rule.id = rule_id
    success = engine.rule_manager.add_rule(rule)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update rule")
    
    return {
        "status": "success",
        "message": f"Rule {rule_id} updated"
    }


@router.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, request: RuleToggleRequest):
    """Enable or disable a rule"""
    engine = get_detection_engine()
    
    if request.enabled:
        success = engine.rule_manager.enable_rule(rule_id)
    else:
        success = engine.rule_manager.disable_rule(rule_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "status": "success",
        "message": f"Rule {rule_id} {'enabled' if request.enabled else 'disabled'}"
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete a custom rule"""
    engine = get_detection_engine()
    
    success = engine.rule_manager.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found or cannot delete default rule")
    
    return {
        "status": "success",
        "message": f"Rule {rule_id} deleted"
    }


@router.get("/rules/stats")
async def get_rules_stats():
    """Get statistics about detection rules"""
    engine = get_detection_engine()
    return engine.rule_manager.get_rule_stats()


@router.post("/test")
async def test_process(request: TestProcessRequest):
    """
    Test a process against detection rules without saving.
    Useful for rule development and testing.
    """
    from models import ProcessCreate
    from datetime import datetime
    
    engine = get_detection_engine()
    
    # Create process object
    process = ProcessCreate(
        process_name=request.process_name,
        parent_name=request.parent_name,
        command_line=request.command_line,
        process_id=request.process_id,
        parent_process_id=request.parent_process_id,
        timestamp=datetime.utcnow()
    )
    
    # Analyze without saving
    results = engine.analyze_process(process)
    
    return {
        "process": {
            "process_name": request.process_name,
            "parent_name": request.parent_name,
            "command_line": request.command_line
        },
        "threats_detected": len(results),
        "results": [
            {
                "is_threat": r.is_threat,
                "rule_name": r.rule.name if r.rule else None,
                "severity": r.rule.severity if r.rule else None,
                "confidence": r.confidence,
                "risk_score": r.risk_score,
                "description": r.rule.description if r.rule else None,
                "details": r.details
            }
            for r in results
        ]
    }


@router.get("/stats")
async def get_detection_stats():
    """Get detection engine statistics"""
    engine = get_detection_engine()
    return engine.get_statistics()


@router.post("/reload")
async def reload_rules():
    """Reload all detection rules from files"""
    engine = get_detection_engine()
    engine.reload_rules()
    
    return {
        "status": "success",
        "message": "Rules reloaded successfully",
        "rules_loaded": len(engine.rule_manager.rules)
    }


@router.post("/export")
async def export_rules(file_path: str = Body(..., embed=True)):
    """Export all rules to a JSON file"""
    engine = get_detection_engine()
    engine.rule_manager.export_rules(file_path)
    
    return {
        "status": "success",
        "message": f"Rules exported to {file_path}"
    }


@router.post("/import")
async def import_rules(file_path: str = Body(..., embed=True)):
    """Import rules from a JSON file"""
    engine = get_detection_engine()
    imported_count = engine.rule_manager.import_rules(file_path)
    
    return {
        "status": "success",
        "message": f"Imported {imported_count} rules",
        "total_rules": len(engine.rule_manager.rules)
    }