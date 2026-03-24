from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProcessBase(BaseModel):
    """Base model for process events"""
    process_name: str = Field(..., description="Name of the process executable")
    parent_name: str = Field(..., description="Name of the parent process")
    command_line: str = Field(..., description="Full command line arguments")
    process_id: int = Field(..., description="Process ID")
    parent_process_id: int = Field(..., description="Parent Process ID")


class ProcessCreate(ProcessBase):
    """Model for creating a new process record"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: Optional[str] = Field(None, description="User who executed the process")
    computer: Optional[str] = Field(None, description="Computer name")


class ProcessEvent(ProcessBase):
    """Full process event model with database ID"""
    id: int
    timestamp: datetime
    user: Optional[str] = None
    computer: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProcessTreeNode(BaseModel):
    """Model for process tree visualization"""
    id: int
    process_name: str
    process_id: int
    parent_process_id: int
    command_line: str
    timestamp: datetime
    children: list = []
    is_suspicious: bool = False
    severity: Optional[str] = None