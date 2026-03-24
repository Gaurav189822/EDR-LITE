"""
Detection Engine Module

Core detection engine that analyzes process events against detection rules.
Implements multiple detection strategies including rule-based matching,
frequency analysis, and behavior scoring.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from models import ProcessCreate, DetectionResult, DetectionRule, RuleType, AlertCreate
from database import Database
from .rules import RuleManager

logger = logging.getLogger(__name__)


class FrequencyTracker:
    """Tracks process creation frequency for anomaly detection"""
    
    def __init__(self, max_age_seconds: int = 300):
        """Initialize frequency tracker"""
        self.max_age_seconds = max_age_seconds
        self.events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
    
    def add_event(self, key: str, timestamp: datetime):
        """Add an event to the tracker"""
        with self._lock:
            self.events[key].append(timestamp)
            self._cleanup_old_events(key, timestamp)
    
    def _cleanup_old_events(self, key: str, current_time: datetime):
        """Remove events older than max_age_seconds"""
        cutoff = current_time - timedelta(seconds=self.max_age_seconds)
        while self.events[key] and self.events[key][0] < cutoff:
            self.events[key].popleft()
    
    def get_count_in_window(self, key: str, window_seconds: int) -> int:
        """Get event count in the specified time window"""
        with self._lock:
            if key not in self.events:
                return 0
            
            cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
            count = sum(1 for ts in self.events[key] if ts > cutoff)
            return count
    
    def get_all_counts(self, window_seconds: int) -> Dict[str, int]:
        """Get counts for all keys"""
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
            return {
                key: sum(1 for ts in timestamps if ts > cutoff)
                for key, timestamps in self.events.items()
            }


class DetectionEngine:
    """Core detection engine for EDR Lite"""
    
    def __init__(self, db: Database = None, rules_directory: str = None):
        """Initialize detection engine"""
        self.db = db or Database()
        self.rule_manager = RuleManager(rules_directory)
        self.frequency_tracker = FrequencyTracker()
        
        # Statistics
        self.events_analyzed = 0
        self.alerts_generated = 0
        self.rules_triggered: Dict[str, int] = defaultdict(int)
        self.start_time = datetime.utcnow()
        
        # Load rules
        self.rule_manager.load_rules()
        
        logger.info("Detection engine initialized")
    
    def analyze_process(self, process: ProcessCreate) -> List[DetectionResult]:
        """
        Analyze a process event against all detection rules.
        Returns list of detection results (may be empty if no threats detected).
        """
        results = []
        start_time = time.time()
        
        # Track for frequency analysis
        self.frequency_tracker.add_event(
            process.parent_name, 
            process.timestamp or datetime.utcnow()
        )
        
        # Get enabled rules
        enabled_rules = self.rule_manager.get_enabled_rules()
        
        for rule in enabled_rules:
            try:
                result = self._evaluate_rule(rule, process)
                if result.is_threat:
                    results.append(result)
                    self.rules_triggered[rule.id] += 1
                    logger.debug(f"Rule {rule.id} triggered for process {process.process_name}")
                    
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")
        
        # Update statistics
        self.events_analyzed += 1
        analysis_time = (time.time() - start_time) * 1000  # ms
        
        if results:
            logger.info(f"Detected {len(results)} threats in {analysis_time:.2f}ms for {process.process_name}")
        
        return results
    
    def _evaluate_rule(self, rule: DetectionRule, process: ProcessCreate) -> DetectionResult:
        """Evaluate a single rule against a process"""
        
        if rule.rule_type == RuleType.PARENT_CHILD:
            return self._evaluate_parent_child_rule(rule, process)
        
        elif rule.rule_type == RuleType.COMMAND_LINE:
            return self._evaluate_command_line_rule(rule, process)
        
        elif rule.rule_type == RuleType.FREQUENCY:
            return self._evaluate_frequency_rule(rule, process)
        
        elif rule.rule_type == RuleType.BEHAVIOR:
            return self._evaluate_behavior_rule(rule, process)
        
        elif rule.rule_type == RuleType.ANOMALY:
            return self._evaluate_anomaly_rule(rule, process)
        
        else:
            return DetectionResult(is_threat=False)
    
    def _evaluate_parent_child_rule(self, rule: DetectionRule, 
                                     process: ProcessCreate) -> DetectionResult:
        """Evaluate parent-child relationship rule"""
        
        # Check parent process match
        if not rule.matches_parent(process.parent_name):
            return DetectionResult(is_threat=False)
        
        # Check child process match
        if not rule.matches_child(process.process_name):
            return DetectionResult(is_threat=False)
        
        # Both matched - threat detected
        return DetectionResult(
            is_threat=True,
            rule=rule,
            confidence=0.9,
            risk_score=rule.risk_score,
            details={
                "parent_process": process.parent_name,
                "child_process": process.process_name,
                "command_line": process.command_line,
                "detection_type": "parent_child_mismatch"
            }
        )
    
    def _evaluate_command_line_rule(self, rule: DetectionRule,
                                     process: ProcessCreate) -> DetectionResult:
        """Evaluate command line pattern rule"""
        
        # Check if child process matches
        if rule.child_process and not rule.matches_child(process.process_name):
            return DetectionResult(is_threat=False)
        
        # Check command line patterns
        if not rule.matches_command_line(process.command_line):
            return DetectionResult(is_threat=False)
        
        return DetectionResult(
            is_threat=True,
            rule=rule,
            confidence=0.85,
            risk_score=rule.risk_score,
            details={
                "process": process.process_name,
                "command_line": process.command_line,
                "detection_type": "suspicious_command_line"
            }
        )
    
    def _evaluate_frequency_rule(self, rule: DetectionRule,
                                  process: ProcessCreate) -> DetectionResult:
        """Evaluate frequency-based rule"""
        
        if not rule.max_events_per_minute:
            return DetectionResult(is_threat=False)
        
        window_seconds = (rule.time_window_minutes or 1) * 60
        count = self.frequency_tracker.get_count_in_window(
            process.parent_name, 
            window_seconds
        )
        
        if count > rule.max_events_per_minute:
            # Calculate dynamic risk score based on excess
            excess = count - rule.max_events_per_minute
            risk_multiplier = min(2.0, 1.0 + (excess / rule.max_events_per_minute))
            risk_score = min(100, int(rule.risk_score * risk_multiplier))
            
            return DetectionResult(
                is_threat=True,
                rule=rule,
                confidence=min(0.95, 0.7 + (excess * 0.05)),
                risk_score=risk_score,
                details={
                    "parent_process": process.parent_name,
                    "event_count": count,
                    "threshold": rule.max_events_per_minute,
                    "time_window_minutes": rule.time_window_minutes,
                    "detection_type": "frequency_anomaly"
                }
            )
        
        return DetectionResult(is_threat=False)
    
    def _evaluate_behavior_rule(self, rule: DetectionRule,
                                 process: ProcessCreate) -> DetectionResult:
        """Evaluate behavior-based rule"""
        
        # Check child process pattern
        if rule.child_process and rule.matches_child(process.process_name):
            return DetectionResult(
                is_threat=True,
                rule=rule,
                confidence=0.75,
                risk_score=rule.risk_score,
                details={
                    "process": process.process_name,
                    "detection_type": "suspicious_behavior"
                }
            )
        
        return DetectionResult(is_threat=False)
    
    def _evaluate_anomaly_rule(self, rule: DetectionRule,
                                process: ProcessCreate) -> DetectionResult:
        """Evaluate anomaly detection rule (placeholder for ML-based detection)"""
        # TODO: Implement ML-based anomaly detection
        return DetectionResult(is_threat=False)
    
    def create_alerts(self, process_id: int, 
                      results: List[DetectionResult]) -> List[AlertCreate]:
        """Create alert objects from detection results"""
        alerts = []
        
        for result in results:
            if result.is_threat and result.rule:
                alert = AlertCreate(
                    process_id=process_id,
                    rule_triggered=result.rule.name,
                    severity=result.rule.severity,
                    description=result.rule.description,
                    risk_score=result.risk_score,
                    details=result.details
                )
                alerts.append(alert)
                self.alerts_generated += 1
        
        return alerts
    
    def process_and_alert(self, process: ProcessCreate) -> Tuple[int, List[AlertCreate]]:
        """
        Full pipeline: analyze process and create alerts.
        Returns (process_id, alerts_created).
        """
        # First, save the process to database
        db_process = self.db.create_process(process)
        
        # Analyze for threats
        results = self.analyze_process(process)
        
        # Create alerts if threats detected
        alerts = self.create_alerts(db_process.id, results)
        
        # Save alerts to database
        for alert in alerts:
            self.db.create_alert(alert)
        
        return db_process.id, alerts
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        uptime = datetime.utcnow() - self.start_time
        
        return {
            "events_analyzed": self.events_analyzed,
            "alerts_generated": self.alerts_generated,
            "uptime_seconds": uptime.total_seconds(),
            "rules_loaded": len(self.rule_manager.rules),
            "rules_enabled": len(self.rule_manager.get_enabled_rules()),
            "top_triggered_rules": dict(sorted(
                self.rules_triggered.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]),
            "frequency_stats": self.frequency_tracker.get_all_counts(300)
        }
    
    def reload_rules(self):
        """Reload all detection rules"""
        self.rule_manager.load_rules()
        logger.info("Detection rules reloaded")
    
    def get_rule_details(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a rule"""
        rule = self.rule_manager.get_rule(rule_id)
        if not rule:
            return None
        
        return {
            "rule": rule.dict(exclude={'_parent_pattern', '_child_pattern', '_cmd_pattern'}),
            "times_triggered": self.rules_triggered.get(rule_id, 0)
        }