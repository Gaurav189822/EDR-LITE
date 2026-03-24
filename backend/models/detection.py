from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Pattern
from datetime import datetime
from enum import Enum
import re


class RuleType(str, Enum):
    """Types of detection rules"""
    PARENT_CHILD = "parent_child"
    COMMAND_LINE = "command_line"
    FREQUENCY = "frequency"
    BEHAVIOR = "behavior"
    ANOMALY = "anomaly"


class DetectionRule(BaseModel):
    """Model for detection rules"""
    id: Optional[str] = Field(None, description="Unique rule identifier")
    name: str = Field(..., description="Rule name")
    rule_type: RuleType = Field(..., description="Type of detection rule")
    description: str = Field(..., description="What this rule detects")
    severity: str = Field(..., description="low/medium/high/critical")
    enabled: bool = Field(default=True, description="Whether rule is active")
    
    # Parent-Child matching
    parent_process: Optional[str] = Field(None, description="Parent process name pattern")
    child_process: Optional[str] = Field(None, description="Child process name pattern")
    
    # Command line matching
    command_line_pattern: Optional[str] = Field(None, description="Regex pattern for command line")
    command_line_contains: Optional[List[str]] = Field(None, description="Strings to match in command line")
    
    # Frequency detection
    max_events_per_minute: Optional[int] = Field(None, description="Threshold for frequency detection")
    time_window_minutes: Optional[int] = Field(default=1, description="Time window for frequency check")
    
    # Risk scoring
    risk_score: int = Field(default=50, ge=0, le=100, description="Base risk score for this rule")
    
    # Compiled patterns (not stored in JSON)
    _parent_pattern: Optional[Pattern] = None
    _child_pattern: Optional[Pattern] = None
    _cmd_pattern: Optional[Pattern] = None
    
    def compile_patterns(self):
        """Compile regex patterns for matching"""
        if self.parent_process:
            self._parent_pattern = re.compile(self.parent_process, re.IGNORECASE)
        if self.child_process:
            self._child_pattern = re.compile(self.child_process, re.IGNORECASE)
        if self.command_line_pattern:
            self._cmd_pattern = re.compile(self.command_line_pattern, re.IGNORECASE)
    
    def matches_parent(self, parent_name: str) -> bool:
        """Check if parent process matches"""
        if not self.parent_process:
            return True
        if not self._parent_pattern:
            self._parent_pattern = re.compile(self.parent_process, re.IGNORECASE)
        return bool(self._parent_pattern.search(parent_name))
    
    def matches_child(self, child_name: str) -> bool:
        """Check if child process matches"""
        if not self.child_process:
            return True
        if not self._child_pattern:
            self._child_pattern = re.compile(self.child_process, re.IGNORECASE)
        return bool(self._child_pattern.search(child_name))
    
    def matches_command_line(self, command_line: str) -> bool:
        """Check if command line matches patterns"""
        if self.command_line_contains:
            return any(s.lower() in command_line.lower() for s in self.command_line_contains)
        if self.command_line_pattern:
            if not self._cmd_pattern:
                self._cmd_pattern = re.compile(self.command_line_pattern, re.IGNORECASE)
            return bool(self._cmd_pattern.search(command_line))
        return True
    
    class Config:
        arbitrary_types_allowed = True


class DetectionResult(BaseModel):
    """Result of detection engine analysis"""
    is_threat: bool = Field(..., description="Whether a threat was detected")
    rule: Optional[DetectionRule] = Field(None, description="Rule that matched")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Detection confidence")
    risk_score: int = Field(default=0, ge=0, le=100, description="Calculated risk score")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional detection details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)