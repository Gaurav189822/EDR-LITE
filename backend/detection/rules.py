"""
Detection Rules Management Module

Manages JSON-driven detection rules for the EDR system.
Supports multiple rule types: parent-child, command line, frequency, and behavior-based.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import logging

from models import DetectionRule, RuleType

logger = logging.getLogger(__name__)


# Default detection rules built into the system
DEFAULT_RULES = [
    # Parent-Child Anomaly Rules
    {
        "id": "RULE-001",
        "name": "Outlook Spawning Shell",
        "rule_type": "parent_child",
        "description": "Microsoft Outlook spawning command shell - possible phishing payload execution",
        "severity": "high",
        "enabled": True,
        "parent_process": "outlook\\.exe",
        "child_process": "cmd\\.exe|powershell\\.exe|wscript\\.exe|cscript\\.exe",
        "risk_score": 80
    },
    {
        "id": "RULE-002",
        "name": "Word Spawning PowerShell",
        "rule_type": "parent_child",
        "description": "Microsoft Word spawning PowerShell - likely malicious macro execution",
        "severity": "critical",
        "enabled": True,
        "parent_process": "winword\\.exe",
        "child_process": "powershell\\.exe|pwsh\\.exe",
        "risk_score": 95
    },
    {
        "id": "RULE-003",
        "name": "Excel Spawning Scripting",
        "rule_type": "parent_child",
        "description": "Microsoft Excel spawning scripting engine - possible malicious macro",
        "severity": "high",
        "enabled": True,
        "parent_process": "excel\\.exe",
        "child_process": "powershell\\.exe|cmd\\.exe|wscript\\.exe|cscript\\.exe|mshta\\.exe",
        "risk_score": 85
    },
    {
        "id": "RULE-004",
        "name": "Browser Spawning Shell",
        "rule_type": "parent_child",
        "description": "Web browser spawning command shell - possible exploit or drive-by download",
        "severity": "high",
        "enabled": True,
        "parent_process": "chrome\\.exe|firefox\\.exe|iexplore\\.exe|msedge\\.exe",
        "child_process": "cmd\\.exe|powershell\\.exe|wscript\\.exe|cscript\\.exe",
        "risk_score": 85
    },
    {
        "id": "RULE-005",
        "name": "LSASS Spawning Shell",
        "rule_type": "parent_child",
        "description": "LSASS spawning command shell - credential dumping or ransomware activity",
        "severity": "critical",
        "enabled": True,
        "parent_process": "lsass\\.exe",
        "child_process": "cmd\\.exe|powershell\\.exe",
        "risk_score": 100
    },
    {
        "id": "RULE-006",
        "name": "Service Host Spawning Regsvr32",
        "rule_type": "parent_child",
        "description": "Service host spawning regsvr32 with potential Squiblydoo technique",
        "severity": "high",
        "enabled": True,
        "parent_process": "svchost\\.exe",
        "child_process": "regsvr32\\.exe",
        "risk_score": 75
    },
    
    # Command Line Analysis Rules
    {
        "id": "RULE-007",
        "name": "Encoded PowerShell Command",
        "rule_type": "command_line",
        "description": "PowerShell with encoded command - common malware obfuscation technique",
        "severity": "high",
        "enabled": True,
        "child_process": "powershell\\.exe|pwsh\\.exe",
        "command_line_contains": ["-enc", "-encodedcommand", "-e ", "-ec "],
        "risk_score": 85
    },
    {
        "id": "RULE-008",
        "name": "PowerShell Download Cradle",
        "rule_type": "command_line",
        "description": "PowerShell downloading content from remote server",
        "severity": "high",
        "enabled": True,
        "child_process": "powershell\\.exe|pwsh\\.exe",
        "command_line_contains": [
            "invoke-webrequest",
            "iwr",
            "wget",
            "curl",
            "net.webclient",
            "downloadstring",
            "downloadfile"
        ],
        "risk_score": 80
    },
    {
        "id": "RULE-009",
        "name": "PowerShell Hidden Window",
        "rule_type": "command_line",
        "description": "PowerShell with hidden window - common malware evasion",
        "severity": "medium",
        "enabled": True,
        "child_process": "powershell\\.exe|pwsh\\.exe",
        "command_line_contains": ["-windowstyle hidden", "-w hidden", "-window hidden"],
        "risk_score": 60
    },
    {
        "id": "RULE-010",
        "name": "PowerShell Bypass Execution Policy",
        "rule_type": "command_line",
        "description": "PowerShell with execution policy bypass",
        "severity": "medium",
        "enabled": True,
        "child_process": "powershell\\.exe|pwsh\\.exe",
        "command_line_contains": ["-executionpolicy bypass", "-ep bypass", "-exec bypass"],
        "risk_score": 65
    },
    {
        "id": "RULE-011",
        "name": "CertUtil Download",
        "rule_type": "command_line",
        "description": "CertUtil used to download files - common LOLBAS technique",
        "severity": "high",
        "enabled": True,
        "child_process": "certutil\\.exe",
        "command_line_contains": ["-urlcache", "-split", "-f"],
        "risk_score": 80
    },
    {
        "id": "RULE-012",
        "name": "MSHTA Execution",
        "rule_type": "command_line",
        "description": "MSHTA executing remote content - common malware vector",
        "severity": "high",
        "enabled": True,
        "child_process": "mshta\\.exe",
        "command_line_contains": ["http", "vbscript", "javascript"],
        "risk_score": 85
    },
    {
        "id": "RULE-013",
        "name": "Regsvr32 Remote Script",
        "rule_type": "command_line",
        "description": "Regsvr32 executing remote scriptlet - Squiblydoo technique",
        "severity": "critical",
        "enabled": True,
        "child_process": "regsvr32\\.exe",
        "command_line_contains": ["/i:http", "scrobj.dll"],
        "risk_score": 95
    },
    {
        "id": "RULE-014",
        "name": "Shadow Copy Deletion",
        "rule_type": "command_line",
        "description": "Command to delete volume shadow copies - ransomware indicator",
        "severity": "critical",
        "enabled": True,
        "child_process": "vssadmin\\.exe|wmic\\.exe",
        "command_line_contains": ["delete shadows", "shadowcopy delete"],
        "risk_score": 100
    },
    {
        "id": "RULE-015",
        "name": "Net User Creation",
        "rule_type": "command_line",
        "description": "Command to create new user account - possible persistence",
        "severity": "high",
        "enabled": True,
        "child_process": "net\\.exe",
        "command_line_contains": ["user", "/add"],
        "risk_score": 75
    },
    {
        "id": "RULE-016",
        "name": "Localgroup Admin Addition",
        "rule_type": "command_line",
        "description": "Command to add user to administrators group",
        "severity": "high",
        "enabled": True,
        "child_process": "net\\.exe",
        "command_line_contains": ["localgroup", "administrators", "/add"],
        "risk_score": 80
    },
    
    # Frequency-based Rules
    {
        "id": "RULE-017",
        "name": "Rapid Process Spawning",
        "rule_type": "frequency",
        "description": "Unusually high rate of process creation from single parent",
        "severity": "medium",
        "enabled": True,
        "max_events_per_minute": 30,
        "time_window_minutes": 1,
        "risk_score": 60
    },
    
    # Behavior-based Rules
    {
        "id": "RULE-018",
        "name": "Suspicious Script Extension",
        "rule_type": "behavior",
        "description": "Execution of script with suspicious extension",
        "severity": "medium",
        "enabled": True,
        "child_process": "\\.(ps1|vbs|js|bat|cmd)$",
        "risk_score": 50
    },
    {
        "id": "RULE-019",
        "name": "Executable in Temp Directory",
        "rule_type": "behavior",
        "description": "Executable running from temporary directory",
        "severity": "medium",
        "enabled": True,
        "child_process": "\\\\Temp\\\\.*\\.exe$|\\\\tmp\\\\.*\\.exe$",
        "risk_score": 55
    },
    {
        "id": "RULE-020",
        "name": "WMI Process Creation",
        "rule_type": "parent_child",
        "description": "WMI creating new process - possible lateral movement",
        "severity": "high",
        "enabled": True,
        "parent_process": "wmiprvse\\.exe|wmiapsrv\\.exe",
        "child_process": "cmd\\.exe|powershell\\.exe|wscript\\.exe",
        "risk_score": 75
    }
]


def load_default_rules() -> List[DetectionRule]:
    """Load the built-in default rules"""
    rules = []
    for rule_data in DEFAULT_RULES:
        try:
            rule = DetectionRule(**rule_data)
            rule.compile_patterns()
            rules.append(rule)
        except Exception as e:
            logger.error(f"Error loading rule {rule_data.get('id')}: {e}")
    
    logger.info(f"Loaded {len(rules)} default detection rules")
    return rules


class RuleManager:
    """Manages detection rules from files and database"""
    
    def __init__(self, rules_directory: str = None):
        """Initialize rule manager"""
        if rules_directory is None:
            rules_directory = os.path.join(
                os.path.dirname(__file__), '..', 'config', 'rules'
            )
        
        self.rules_directory = Path(rules_directory)
        self.rules: List[DetectionRule] = []
        self.rules_by_id: Dict[str, DetectionRule] = {}
        self.last_reload: Optional[datetime] = None
        
        # Ensure rules directory exists
        self.rules_directory.mkdir(parents=True, exist_ok=True)
    
    def load_rules(self, include_defaults: bool = True) -> List[DetectionRule]:
        """Load all rules from files and defaults"""
        self.rules = []
        
        # Load default rules first
        if include_defaults:
            default_rules = load_default_rules()
            self.rules.extend(default_rules)
            logger.info(f"Loaded {len(default_rules)} default rules")
        
        # Load custom rules from files
        custom_rules = self._load_rules_from_files()
        self.rules.extend(custom_rules)
        
        # Build ID index
        self.rules_by_id = {rule.id: rule for rule in self.rules if rule.id}
        
        self.last_reload = datetime.utcnow()
        
        enabled_count = sum(1 for r in self.rules if r.enabled)
        logger.info(f"Total rules loaded: {len(self.rules)} ({enabled_count} enabled)")
        
        return self.rules
    
    def _load_rules_from_files(self) -> List[DetectionRule]:
        """Load rules from JSON files in rules directory"""
        custom_rules = []
        
        if not self.rules_directory.exists():
            return custom_rules
        
        for rule_file in self.rules_directory.glob("*.json"):
            try:
                with open(rule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle both single rule and array of rules
                rules_data = data if isinstance(data, list) else [data]
                
                for rule_data in rules_data:
                    rule = DetectionRule(**rule_data)
                    rule.compile_patterns()
                    custom_rules.append(rule)
                
                logger.info(f"Loaded {len(rules_data)} rules from {rule_file.name}")
                
            except Exception as e:
                logger.error(f"Error loading rules from {rule_file}: {e}")
        
        return custom_rules
    
    def get_rule(self, rule_id: str) -> Optional[DetectionRule]:
        """Get a rule by ID"""
        return self.rules_by_id.get(rule_id)
    
    def get_enabled_rules(self) -> List[DetectionRule]:
        """Get all enabled rules"""
        return [rule for rule in self.rules if rule.enabled]
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[DetectionRule]:
        """Get rules filtered by type"""
        return [rule for rule in self.rules 
                if rule.rule_type == rule_type and rule.enabled]
    
    def add_rule(self, rule: DetectionRule) -> bool:
        """Add a new custom rule"""
        try:
            # Compile patterns
            rule.compile_patterns()
            
            # Add to memory
            self.rules.append(rule)
            if rule.id:
                self.rules_by_id[rule.id] = rule
            
            # Save to file
            self._save_rule_to_file(rule)
            
            logger.info(f"Added rule: {rule.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding rule: {e}")
            return False
    
    def _save_rule_to_file(self, rule: DetectionRule):
        """Save a rule to a JSON file"""
        if not rule.id:
            return
        
        file_path = self.rules_directory / f"{rule.id}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(rule.dict(exclude={'_parent_pattern', '_child_pattern', '_cmd_pattern'}), 
                     f, indent=2)
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule by ID"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            self._save_rule_to_file(rule)
            logger.info(f"Disabled rule: {rule_id}")
            return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule by ID"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            self._save_rule_to_file(rule)
            logger.info(f"Enabled rule: {rule_id}")
            return True
        return False
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a custom rule"""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        
        # Remove from memory
        self.rules = [r for r in self.rules if r.id != rule_id]
        if rule_id in self.rules_by_id:
            del self.rules_by_id[rule_id]
        
        # Delete file
        file_path = self.rules_directory / f"{rule_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        logger.info(f"Deleted rule: {rule_id}")
        return True
    
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules"""
        stats = {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "disabled_rules": sum(1 for r in self.rules if not r.enabled),
            "by_type": {},
            "by_severity": {},
            "last_reload": self.last_reload.isoformat() if self.last_reload else None
        }
        
        for rule in self.rules:
            # Count by type
            rule_type = rule.rule_type.value
            stats["by_type"][rule_type] = stats["by_type"].get(rule_type, 0) + 1
            
            # Count by severity
            severity = rule.severity
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
        
        return stats
    
    def export_rules(self, file_path: str):
        """Export all rules to a JSON file"""
        export_data = []
        for rule in self.rules:
            rule_dict = rule.dict(
                exclude={'_parent_pattern', '_child_pattern', '_cmd_pattern'}
            )
            export_data.append(rule_dict)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported {len(export_data)} rules to {file_path}")
    
    def import_rules(self, file_path: str) -> int:
        """Import rules from a JSON file"""
        imported = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        rules_data = data if isinstance(data, list) else [data]
        
        for rule_data in rules_data:
            try:
                rule = DetectionRule(**rule_data)
                self.add_rule(rule)
                imported += 1
            except Exception as e:
                logger.error(f"Error importing rule: {e}")
        
        logger.info(f"Imported {imported} rules from {file_path}")
        return imported