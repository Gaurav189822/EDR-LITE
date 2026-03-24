from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class ProcessModel(Base):
    """Database model for process events"""
    __tablename__ = "processes"
    
    id = Column(Integer, primary_key=True, index=True)
    process_name = Column(String(255), nullable=False, index=True)
    parent_name = Column(String(255), nullable=False, index=True)
    command_line = Column(Text, nullable=False)
    process_id = Column(Integer, nullable=False)
    parent_process_id = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    user = Column(String(255), nullable=True)
    computer = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "process_name": self.process_name,
            "parent_name": self.parent_name,
            "command_line": self.command_line,
            "process_id": self.process_id,
            "parent_process_id": self.parent_process_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user": self.user,
            "computer": self.computer,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AlertModel(Base):
    """Database model for security alerts"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, nullable=False, index=True)
    rule_triggered = Column(String(255), nullable=False, index=True)
    severity = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    risk_score = Column(Integer, default=0)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    acknowledged = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "process_id": self.process_id,
            "rule_triggered": self.rule_triggered,
            "severity": self.severity,
            "description": self.description,
            "risk_score": self.risk_score,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "acknowledged": self.acknowledged
        }


class RuleExecutionLog(Base):
    """Log of rule executions for debugging and auditing"""
    __tablename__ = "rule_execution_logs"
    
    id = Column(Integer, primary_key=True)
    rule_id = Column(String(255), nullable=False)
    rule_name = Column(String(255), nullable=False)
    process_id = Column(Integer, nullable=False)
    matched = Column(Boolean, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=func.now())