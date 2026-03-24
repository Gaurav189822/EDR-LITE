"""
Processes API Routes

REST API endpoints for process event retrieval and management.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from database import get_db
from database.models import ProcessModel
from models import ProcessEvent, ProcessTreeNode

router = APIRouter(prefix="/api/processes", tags=["processes"])


@router.get("", response_model=List[ProcessEvent])
async def get_processes(
    limit: int = Query(100, ge=1, le=1000, description="Number of processes to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search in process names and command lines"),
    session: AsyncSession = Depends(get_db)
):
    """
    Get process events with optional filtering.
    
    - **limit**: Maximum number of processes to return (1-1000)
    - **offset**: Pagination offset
    - **search**: Search string for process name, parent name, or command line
    """
    from database.database import db
    
    processes = await db.get_processes_async(
        session, 
        limit=limit, 
        offset=offset,
        search=search
    )
    
    return [ProcessEvent.model_validate(p) for p in processes]


@router.get("/recent")
async def get_recent_processes(
    minutes: int = Query(5, ge=1, le=1440, description="Time window in minutes"),
    session: AsyncSession = Depends(get_db)
):
    """Get processes from the last N minutes"""
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    
    result = await session.execute(
        select(ProcessModel)
        .where(ProcessModel.timestamp >= cutoff)
        .order_by(desc(ProcessModel.timestamp))
    )
    
    processes = result.scalars().all()
    return [ProcessEvent.model_validate(p) for p in processes]


@router.get("/stats")
async def get_process_stats(session: AsyncSession = Depends(get_db)):
    """Get process statistics"""
    from datetime import timedelta
    
    # Total processes
    result = await session.execute(select(func.count(ProcessModel.id)))
    total_processes = result.scalar()
    
    # Processes in last hour
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    result = await session.execute(
        select(func.count(ProcessModel.id)).where(ProcessModel.timestamp >= hour_ago)
    )
    processes_last_hour = result.scalar()
    
    # Processes in last 24 hours
    day_ago = datetime.utcnow() - timedelta(hours=24)
    result = await session.execute(
        select(func.count(ProcessModel.id)).where(ProcessModel.timestamp >= day_ago)
    )
    processes_last_day = result.scalar()
    
    # Top parent processes
    result = await session.execute(
        select(ProcessModel.parent_name, func.count(ProcessModel.id))
        .group_by(ProcessModel.parent_name)
        .order_by(desc(func.count(ProcessModel.id)))
        .limit(10)
    )
    top_parents = [{"name": name, "count": count} for name, count in result.all()]
    
    # Top child processes
    result = await session.execute(
        select(ProcessModel.process_name, func.count(ProcessModel.id))
        .group_by(ProcessModel.process_name)
        .order_by(desc(func.count(ProcessModel.id)))
        .limit(10)
    )
    top_children = [{"name": name, "count": count} for name, count in result.all()]
    
    return {
        "total_processes": total_processes,
        "processes_last_hour": processes_last_hour,
        "processes_last_24h": processes_last_day,
        "top_parent_processes": top_parents,
        "top_child_processes": top_children
    }


@router.get("/{process_id}", response_model=ProcessEvent)
async def get_process(
    process_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get a specific process by ID"""
    process = await session.get(ProcessModel, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    return ProcessEvent.model_validate(process)


@router.get("/{process_id}/tree")
async def get_process_tree(
    process_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get process tree starting from a specific process"""
    from database.models import AlertModel
    from sqlalchemy import or_
    
    # Get the root process
    root = await session.get(ProcessModel, process_id)
    if not root:
        raise HTTPException(status_code=404, detail="Process not found")
    
    # Get related alerts for this process
    result = await session.execute(
        select(AlertModel).where(AlertModel.process_id == process_id)
    )
    alerts = result.scalars().all()
    
    # Build tree node
    is_suspicious = len(alerts) > 0
    severity = alerts[0].severity if alerts else None
    
    tree = ProcessTreeNode(
        id=root.id,
        process_name=root.process_name,
        process_id=root.process_id,
        parent_process_id=root.parent_process_id,
        command_line=root.command_line,
        timestamp=root.timestamp,
        is_suspicious=is_suspicious,
        severity=severity
    )
    
    # Find child processes (processes where this is the parent)
    result = await session.execute(
        select(ProcessModel).where(
            ProcessModel.parent_process_id == root.process_id
        ).order_by(desc(ProcessModel.timestamp)).limit(50)
    )
    children = result.scalars().all()
    
    # Recursively build tree (limit depth)
    tree.children = await _build_tree_recursive(session, children, depth=0, max_depth=3)
    
    return tree


async def _build_tree_recursive(session, processes, depth: int, max_depth: int):
    """Recursively build process tree"""
    from database.models import AlertModel
    
    if depth >= max_depth or not processes:
        return []
    
    nodes = []
    for proc in processes:
        # Check for alerts
        result = await session.execute(
            select(AlertModel).where(AlertModel.process_id == proc.id)
        )
        alerts = result.scalars().all()
        
        is_suspicious = len(alerts) > 0
        severity = alerts[0].severity if alerts else None
        
        node = ProcessTreeNode(
            id=proc.id,
            process_name=proc.process_name,
            process_id=proc.process_id,
            parent_process_id=proc.parent_process_id,
            command_line=proc.command_line,
            timestamp=proc.timestamp,
            is_suspicious=is_suspicious,
            severity=severity
        )
        
        # Get children
        result = await session.execute(
            select(ProcessModel).where(
                ProcessModel.parent_process_id == proc.process_id
            ).order_by(desc(ProcessModel.timestamp)).limit(20)
        )
        children = result.scalars().all()
        
        if children:
            node.children = await _build_tree_recursive(session, children, depth + 1, max_depth)
        
        nodes.append(node)
    
    return nodes


@router.get("/by-parent/{parent_name}")
async def get_processes_by_parent(
    parent_name: str,
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db)
):
    """Get processes spawned by a specific parent"""
    result = await session.execute(
        select(ProcessModel)
        .where(ProcessModel.parent_name.contains(parent_name))
        .order_by(desc(ProcessModel.timestamp))
        .limit(limit)
    )
    
    processes = result.scalars().all()
    return [ProcessEvent.model_validate(p) for p in processes]


@router.delete("/{process_id}")
async def delete_process(
    process_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete a process record"""
    process = await session.get(ProcessModel, process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    
    await session.delete(process)
    await session.commit()
    
    return {"status": "success", "message": f"Process {process_id} deleted"}