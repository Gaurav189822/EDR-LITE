"""
Sysmon Log Parser Module

Parses Windows Sysmon Event ID 1 (Process Creation) events from:
- EVTX files (Windows Event Log format)
- XML exports
- JSON exports
- Real-time Windows Event Log API (when available)
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Iterator, Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class SysmonEvent:
    """Represents a parsed Sysmon Event ID 1 (Process Creation)"""
    event_id: int
    timestamp: datetime
    computer: str
    user: str
    process_id: int
    process_name: str
    command_line: str
    parent_process_id: int
    parent_process_name: str
    parent_command_line: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha256: Optional[str] = None
    integrity_level: Optional[str] = None
    original_file_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "computer": self.computer,
            "user": self.user,
            "process_id": self.process_id,
            "process_name": self.process_name,
            "command_line": self.command_line,
            "parent_process_id": self.parent_process_id,
            "parent_process_name": self.parent_process_name,
            "parent_command_line": self.parent_command_line,
            "hash_md5": self.hash_md5,
            "hash_sha256": self.hash_sha256,
            "integrity_level": self.integrity_level,
            "original_file_name": self.original_file_name
        }


class SysmonParser:
    """Parser for Sysmon Event Logs"""
    
    # Sysmon Event ID for Process Creation
    EVENT_ID_PROCESS_CREATE = 1
    
    # Common Sysmon field mappings
    FIELD_MAPPINGS = {
        'ProcessId': 'process_id',
        'ProcessGuid': 'process_guid',
        'Image': 'process_name',
        'CommandLine': 'command_line',
        'CurrentDirectory': 'current_directory',
        'User': 'user',
        'LogonGuid': 'logon_guid',
        'LogonId': 'logon_id',
        'TerminalSessionId': 'terminal_session_id',
        'IntegrityLevel': 'integrity_level',
        'Hashes': 'hashes',
        'ParentProcessGuid': 'parent_process_guid',
        'ParentProcessId': 'parent_process_id',
        'ParentImage': 'parent_process_name',
        'ParentCommandLine': 'parent_command_line',
        'ParentUser': 'parent_user',
        'UtcTime': 'utc_time',
        'OriginalFileName': 'original_file_name',
        'Company': 'company',
        'Description': 'description',
        'Product': 'product'
    }
    
    def __init__(self):
        self.events_parsed = 0
        self.errors = []
    
    def parse_evtx_file(self, file_path: str) -> Iterator[SysmonEvent]:
        """
        Parse Sysmon events from an EVTX file.
        Requires python-evtx library.
        """
        try:
            from Evtx.Evtx import Evtx
            from Evtx.Views import evtx_file_xml_view
        except ImportError:
            logger.error("python-evtx library not installed. Install with: pip install python-evtx")
            return
        
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        logger.info(f"Parsing EVTX file: {file_path}")
        
        try:
            with Evtx(str(file_path)) as evtx:
                for xml_record in evtx_file_xml_view(evtx.get_record_header()):
                    try:
                        event = self._parse_xml_event(xml_record)
                        if event and event.event_id == self.EVENT_ID_PROCESS_CREATE:
                            self.events_parsed += 1
                            yield event
                    except Exception as e:
                        self.errors.append(f"Error parsing record: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error reading EVTX file: {e}")
            self.errors.append(f"EVTX read error: {e}")
    
    def parse_xml_file(self, file_path: str) -> Iterator[SysmonEvent]:
        """Parse Sysmon events from an XML export file"""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        logger.info(f"Parsing XML file: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Handle different XML structures
            events = root.findall('.//Event') or root.findall('.//{*}Event') or [root]
            
            for event_elem in events:
                try:
                    event = self._parse_xml_element(event_elem)
                    if event and event.event_id == self.EVENT_ID_PROCESS_CREATE:
                        self.events_parsed += 1
                        yield event
                except Exception as e:
                    self.errors.append(f"Error parsing XML event: {e}")
                    continue
                    
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            self.errors.append(f"XML parse error: {e}")
        except Exception as e:
            logger.error(f"Error reading XML file: {e}")
            self.errors.append(f"XML read error: {e}")
    
    def parse_json_file(self, file_path: str) -> Iterator[SysmonEvent]:
        """Parse Sysmon events from a JSON export file"""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return
        
        logger.info(f"Parsing JSON file: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both single event and array of events
            events = data if isinstance(data, list) else [data]
            
            for event_data in events:
                try:
                    event = self._parse_json_event(event_data)
                    if event and event.event_id == self.EVENT_ID_PROCESS_CREATE:
                        self.events_parsed += 1
                        yield event
                except Exception as e:
                    self.errors.append(f"Error parsing JSON event: {e}")
                    continue
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            self.errors.append(f"JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
            self.errors.append(f"JSON read error: {e}")
    
    def parse_json_line(self, line: str) -> Optional[SysmonEvent]:
        """Parse a single JSON line (for streaming)"""
        try:
            data = json.loads(line)
            event = self._parse_json_event(data)
            if event and event.event_id == self.EVENT_ID_PROCESS_CREATE:
                self.events_parsed += 1
                return event
        except Exception as e:
            self.errors.append(f"Error parsing JSON line: {e}")
        return None
    
    def _parse_xml_event(self, xml_string: str) -> Optional[SysmonEvent]:
        """Parse an XML event string"""
        try:
            root = ET.fromstring(xml_string)
            return self._parse_xml_element(root)
        except ET.ParseError:
            return None
    
    def _parse_xml_element(self, event_elem: ET.Element) -> Optional[SysmonEvent]:
        """Parse an XML Event element"""
        # Define namespaces
        ns = {
            'e': 'http://schemas.microsoft.com/win/2004/08/events/event'
        }
        
        # Get Event ID
        event_id_elem = event_elem.find('.//e:EventID', ns) or event_elem.find('.//EventID')
        if event_id_elem is None:
            return None
        
        try:
            event_id = int(event_id_elem.text)
        except (ValueError, TypeError):
            return None
        
        # Only process Event ID 1 (Process Creation)
        if event_id != self.EVENT_ID_PROCESS_CREATE:
            return None
        
        # Get System data
        system_elem = event_elem.find('.//e:System', ns) or event_elem.find('.//System')
        computer = self._get_xml_text(system_elem, './/e:Computer', ns) or \
                   self._get_xml_text(system_elem, './/Computer') or 'UNKNOWN'
        
        time_created = self._get_xml_text(system_elem, './/e:TimeCreated/@SystemTime', ns) or \
                       self._get_xml_text(system_elem, './/TimeCreated/@SystemTime')
        timestamp = self._parse_timestamp(time_created) or datetime.utcnow()
        
        # Get EventData
        event_data = {}
        data_elem = event_elem.find('.//e:EventData', ns) or event_elem.find('.//EventData')
        if data_elem is not None:
            for data in data_elem.findall('.//e:Data', ns) or data_elem.findall('.//Data'):
                name = data.get('Name')
                if name:
                    event_data[name] = data.text or ''
        
        return self._create_event_from_data(event_id, timestamp, computer, event_data)
    
    def _parse_json_event(self, data: Dict[str, Any]) -> Optional[SysmonEvent]:
        """Parse a JSON event dictionary"""
        # Handle different JSON structures
        event_data = {}
        
        # Try to extract Event ID
        event_id = data.get('EventID') or data.get('event_id')
        if event_id is None:
            event_data_elem = data.get('EventData') or data.get('event_data', {})
            event_id = event_data_elem.get('EventID')
        
        if event_id is None:
            return None
        
        try:
            event_id = int(event_id)
        except (ValueError, TypeError):
            return None
        
        # Get timestamp
        timestamp_str = data.get('TimeCreated') or data.get('time_created') or \
                       data.get('UtcTime') or data.get('timestamp')
        timestamp = self._parse_timestamp(timestamp_str) or datetime.utcnow()
        
        # Get computer name
        computer = data.get('Computer') or data.get('computer') or 'UNKNOWN'
        
        # Extract EventData fields
        event_data_elem = data.get('EventData') or data.get('event_data', {})
        if isinstance(event_data_elem, dict):
            event_data.update(event_data_elem)
        
        # Also check for direct fields
        for key, value in data.items():
            if key not in event_data:
                event_data[key] = value
        
        return self._create_event_from_data(event_id, timestamp, computer, event_data)
    
    def _create_event_from_data(self, event_id: int, timestamp: datetime, 
                                computer: str, data: Dict[str, str]) -> SysmonEvent:
        """Create a SysmonEvent from parsed data"""
        # Extract hashes
        hashes = data.get('Hashes', '')
        hash_md5 = None
        hash_sha256 = None
        
        if hashes:
            md5_match = re.search(r'MD5=([A-Fa-f0-9]{32})', hashes)
            sha256_match = re.search(r'SHA256=([A-Fa-f0-9]{64})', hashes)
            if md5_match:
                hash_md5 = md5_match.group(1)
            if sha256_match:
                hash_sha256 = sha256_match.group(1)
        
        return SysmonEvent(
            event_id=event_id,
            timestamp=timestamp,
            computer=computer,
            user=data.get('User', 'SYSTEM'),
            process_id=self._parse_int(data.get('ProcessId', '0')),
            process_name=data.get('Image', 'unknown'),
            command_line=data.get('CommandLine', ''),
            parent_process_id=self._parse_int(data.get('ParentProcessId', '0')),
            parent_process_name=data.get('ParentImage', 'unknown'),
            parent_command_line=data.get('ParentCommandLine'),
            hash_md5=hash_md5,
            hash_sha256=hash_sha256,
            integrity_level=data.get('IntegrityLevel'),
            original_file_name=data.get('OriginalFileName')
        )
    
    def _get_xml_text(self, elem: Optional[ET.Element], path: str, 
                      ns: Dict[str, str] = None) -> Optional[str]:
        """Safely get text from XML element"""
        if elem is None:
            return None
        found = elem.find(path, ns) if ns else elem.find(path)
        if found is not None:
            return found.text
        return None
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse various timestamp formats"""
        if not timestamp_str:
            return None
        
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%m/%d/%Y %I:%M:%S %p'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # Try ISO format
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        return None
    
    def _parse_int(self, value: str) -> int:
        """Safely parse integer"""
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics"""
        return {
            "events_parsed": self.events_parsed,
            "errors": len(self.errors),
            "error_details": self.errors[:10]  # Return first 10 errors
        }
    
    def reset_stats(self):
        """Reset parser statistics"""
        self.events_parsed = 0
        self.errors = []