# System Architecture

<cite>
**Referenced Files in This Document**
- [backend/main.py](file://backend/main.py)
- [backend/database/database.py](file://backend/database/database.py)
- [backend/detection/engine.py](file://backend/detection/engine.py)
- [backend/detection/rules.py](file://backend/detection/rules.py)
- [backend/parser/sysmon_parser.py](file://backend/parser/sysmon_parser.py)
- [backend/parser/log_simulator.py](file://backend/parser/log_simulator.py)
- [backend/routes/websocket.py](file://backend/routes/websocket.py)
- [backend/routes/alerts.py](file://backend/routes/alerts.py)
- [backend/routes/processes.py](file://backend/routes/processes.py)
- [backend/routes/detection.py](file://backend/routes/detection.py)
- [backend/models/alert.py](file://backend/models/alert.py)
- [backend/models/process.py](file://backend/models/process.py)
- [backend/models/detection.py](file://backend/models/detection.py)
- [frontend/src/api/client.ts](file://frontend/src/api/client.ts)
- [frontend/src/hooks/useWebSocket.ts](file://frontend/src/hooks/useWebSocket.ts)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document describes the system architecture of EDR Lite, a lightweight Endpoint Detection and Response platform. It outlines the high-level layered architecture combining a FastAPI backend with a React frontend, real-time WebSocket communication, and a SQLite-backed persistence layer. The system ingests Sysmon process creation events, parses them, applies configurable detection rules, stores outcomes in a database, and streams live updates to the dashboard. Cross-cutting concerns include security, monitoring, and performance optimization strategies.

## Project Structure
The repository follows a clear separation of concerns:
- Backend: FastAPI application with routers, database, detection engine, parser, and models.
- Frontend: React SPA using TypeScript and Vite, communicating with the backend via Axios and WebSocket hooks.
- Sample data: JSON sample Sysmon events for demonstration and testing.

```mermaid
graph TB
subgraph "Backend"
A["FastAPI App<br/>backend/main.py"]
B["Routes<br/>routes/*.py"]
C["Detection Engine<br/>detection/engine.py"]
D["Rules Manager<br/>detection/rules.py"]
E["Database Layer<br/>database/database.py"]
F["Parser<br/>parser/sysmon_parser.py"]
G["Simulator<br/>parser/log_simulator.py"]
H["Models<br/>models/*.py"]
end
subgraph "Frontend"
X["API Client<br/>frontend/src/api/client.ts"]
Y["WebSocket Hook<br/>frontend/src/hooks/useWebSocket.ts"]
end
X --> A
Y --> A
A --> B
B --> C
C --> D
C --> E
F --> A
G --> A
A --> H
```

**Diagram sources**
- [backend/main.py:171-192](file://backend/main.py#L171-L192)
- [backend/routes/alerts.py:15](file://backend/routes/alerts.py#L15)
- [backend/routes/processes.py:16](file://backend/routes/processes.py#L16)
- [backend/routes/detection.py:14](file://backend/routes/detection.py#L14)
- [backend/detection/engine.py:64-82](file://backend/detection/engine.py#L64-L82)
- [backend/detection/rules.py:273-313](file://backend/detection/rules.py#L273-L313)
- [backend/database/database.py:21-70](file://backend/database/database.py#L21-L70)
- [backend/parser/sysmon_parser.py:61-95](file://backend/parser/sysmon_parser.py#L61-L95)
- [backend/parser/log_simulator.py:18-37](file://backend/parser/log_simulator.py#L18-L37)
- [backend/models/alert.py:15-38](file://backend/models/alert.py#L15-L38)
- [backend/models/process.py:6-31](file://backend/models/process.py#L6-L31)
- [backend/models/detection.py:17-92](file://backend/models/detection.py#L17-L92)
- [frontend/src/api/client.ts:1-124](file://frontend/src/api/client.ts#L1-L124)
- [frontend/src/hooks/useWebSocket.ts:1-103](file://frontend/src/hooks/useWebSocket.ts#L1-L103)

**Section sources**
- [backend/main.py:171-192](file://backend/main.py#L171-L192)
- [backend/database/database.py:21-70](file://backend/database/database.py#L21-L70)
- [backend/detection/engine.py:64-82](file://backend/detection/engine.py#L64-L82)
- [backend/detection/rules.py:273-313](file://backend/detection/rules.py#L273-L313)
- [backend/parser/sysmon_parser.py:61-95](file://backend/parser/sysmon_parser.py#L61-L95)
- [backend/parser/log_simulator.py:18-37](file://backend/parser/log_simulator.py#L18-L37)
- [backend/routes/websocket.py:14-65](file://backend/routes/websocket.py#L14-L65)
- [backend/models/alert.py:15-38](file://backend/models/alert.py#L15-L38)
- [backend/models/process.py:6-31](file://backend/models/process.py#L6-L31)
- [backend/models/detection.py:17-92](file://backend/models/detection.py#L17-L92)
- [frontend/src/api/client.ts:1-124](file://frontend/src/api/client.ts#L1-L124)
- [frontend/src/hooks/useWebSocket.ts:1-103](file://frontend/src/hooks/useWebSocket.ts#L1-L103)

## Core Components
- FastAPI Application: Orchestrates startup/shutdown, mounts routers, configures CORS, and exposes health and stats endpoints.
- Database Layer: Singleton manager using SQLAlchemy and aiosqlite for SQLite, providing sync and async sessions and CRUD operations.
- Detection Engine: Evaluates incoming process events against JSON-driven rules, tracks frequency anomalies, and generates alerts.
- Rules Manager: Loads default and custom rules from JSON files, supports enabling/disabling, exporting/importing, and runtime reload.
- Parser: Parses Sysmon events from EVTX/XML/JSON formats and normalizes to internal models.
- Log Simulator: Generates synthetic Sysmon events for testing and demonstration.
- WebSocket Routes: Real-time streaming of alerts and process events to connected clients.
- API Routers: REST endpoints for alerts, processes, detection rules, and ingestion.
- Frontend API Client and WebSocket Hook: Axios-based HTTP client and reusable WebSocket hook for real-time updates.

**Section sources**
- [backend/main.py:120-169](file://backend/main.py#L120-L169)
- [backend/database/database.py:21-324](file://backend/database/database.py#L21-L324)
- [backend/detection/engine.py:64-324](file://backend/detection/engine.py#L64-L324)
- [backend/detection/rules.py:273-480](file://backend/detection/rules.py#L273-L480)
- [backend/parser/sysmon_parser.py:61-385](file://backend/parser/sysmon_parser.py#L61-L385)
- [backend/parser/log_simulator.py:18-315](file://backend/parser/log_simulator.py#L18-L315)
- [backend/routes/websocket.py:14-233](file://backend/routes/websocket.py#L14-L233)
- [backend/routes/alerts.py:15-180](file://backend/routes/alerts.py#L15-L180)
- [backend/routes/processes.py:16-253](file://backend/routes/processes.py#L16-L253)
- [backend/routes/detection.py:14-256](file://backend/routes/detection.py#L14-L256)
- [frontend/src/api/client.ts:1-124](file://frontend/src/api/client.ts#L1-L124)
- [frontend/src/hooks/useWebSocket.ts:1-103](file://frontend/src/hooks/useWebSocket.ts#L1-L103)

## Architecture Overview
EDR Lite employs a layered architecture:
- Presentation Layer: React SPA with Axios for REST and WebSocket for live updates.
- Application Layer: FastAPI routes delegate to the detection engine and database layer.
- Domain Layer: Detection engine encapsulates rule evaluation and alert generation.
- Persistence Layer: SQLite via SQLAlchemy and aiosqlite for lightweight deployment.

```mermaid
graph TB
subgraph "Presentation"
FE["React SPA<br/>frontend/src/*"]
end
subgraph "Application"
API["FastAPI App<br/>backend/main.py"]
WS["WebSocket Routes<br/>routes/websocket.py"]
R_ALERTS["Alerts Router<br/>routes/alerts.py"]
R_PROCESSES["Processes Router<br/>routes/processes.py"]
R_DETECTION["Detection Router<br/>routes/detection.py"]
end
subgraph "Domain"
DET["Detection Engine<br/>detection/engine.py"]
RULES["Rules Manager<br/>detection/rules.py"]
end
subgraph "Persistence"
DB["Database Manager<br/>database/database.py"]
end
subgraph "Data Ingestion"
PARSER["Sysmon Parser<br/>parser/sysmon_parser.py"]
SIM["Log Simulator<br/>parser/log_simulator.py"]
end
FE --> API
FE --> WS
API --> R_ALERTS
API --> R_PROCESSES
API --> R_DETECTION
API --> WS
R_ALERTS --> DB
R_PROCESSES --> DB
R_DETECTION --> DET
DET --> RULES
DET --> DB
PARSER --> API
SIM --> API
```

**Diagram sources**
- [backend/main.py:171-192](file://backend/main.py#L171-L192)
- [backend/routes/websocket.py:14-65](file://backend/routes/websocket.py#L14-L65)
- [backend/routes/alerts.py:15-180](file://backend/routes/alerts.py#L15-L180)
- [backend/routes/processes.py:16-253](file://backend/routes/processes.py#L16-L253)
- [backend/routes/detection.py:14-256](file://backend/routes/detection.py#L14-L256)
- [backend/detection/engine.py:64-82](file://backend/detection/engine.py#L64-L82)
- [backend/detection/rules.py:273-313](file://backend/detection/rules.py#L273-L313)
- [backend/database/database.py:21-70](file://backend/database/database.py#L21-L70)
- [backend/parser/sysmon_parser.py:61-95](file://backend/parser/sysmon_parser.py#L61-L95)
- [backend/parser/log_simulator.py:18-37](file://backend/parser/log_simulator.py#L18-L37)

## Detailed Component Analysis

### FastAPI Application Lifecycle and Endpoints
- Startup: Initializes database, detection engine, optional log simulator, and background monitoring task when simulation mode is enabled.
- Health and Stats: Provides health status and combined engine/rule statistics.
- Manual Ingestion: Accepts Sysmon events and triggers detection and broadcasting.
- Simulation Controls: Toggle simulation mode and generate batch events.

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "FastAPI App"
participant Engine as "DetectionEngine"
participant DB as "Database"
participant WS as "WebSocket"
Client->>API : "POST /api/ingest"
API->>Engine : "process_and_alert(ProcessCreate)"
Engine->>DB : "create_process()"
Engine->>Engine : "analyze_process()"
Engine->>DB : "create_alert() for each DetectionResult"
Engine-->>API : "(process_id, alerts)"
API->>WS : "broadcast_alert()/broadcast_event()"
API-->>Client : "{status, process_id, alerts_generated}"
```

**Diagram sources**
- [backend/main.py:243-311](file://backend/main.py#L243-L311)
- [backend/detection/engine.py:272-290](file://backend/detection/engine.py#L272-L290)
- [backend/database/database.py:86-215](file://backend/database/database.py#L86-L215)
- [backend/routes/websocket.py:209-224](file://backend/routes/websocket.py#L209-L224)

**Section sources**
- [backend/main.py:120-169](file://backend/main.py#L120-L169)
- [backend/main.py:214-241](file://backend/main.py#L214-L241)
- [backend/main.py:243-358](file://backend/main.py#L243-L358)

### Detection Engine and Rules Management
- Detection Engine: Tracks frequency anomalies, evaluates multiple rule types (parent-child, command line, frequency, behavior, anomaly), and aggregates statistics.
- Rules Manager: Loads default and custom rules from JSON, compiles patterns, and supports CRUD operations and runtime reload.

```mermaid
classDiagram
class DetectionEngine {
+analyze_process(process) DetectionResult[]
+process_and_alert(process) (int, AlertCreate[])
+get_statistics() Dict
+reload_rules() void
}
class RuleManager {
+load_rules(include_defaults) DetectionRule[]
+get_enabled_rules() DetectionRule[]
+add_rule(rule) bool
+enable_rule(id) bool
+disable_rule(id) bool
+delete_rule(id) bool
+get_rule_stats() Dict
+export_rules(path) void
+import_rules(path) int
}
DetectionEngine --> RuleManager : "uses"
```

**Diagram sources**
- [backend/detection/engine.py:64-324](file://backend/detection/engine.py#L64-L324)
- [backend/detection/rules.py:273-480](file://backend/detection/rules.py#L273-L480)

**Section sources**
- [backend/detection/engine.py:64-324](file://backend/detection/engine.py#L64-L324)
- [backend/detection/rules.py:258-480](file://backend/detection/rules.py#L258-L480)

### Database Layer and Data Models
- Database Manager: Singleton with sync and async engines, table creation, and CRUD helpers for processes and alerts.
- Models: Pydantic models define alert severity, process event structure, and detection rule schema.

```mermaid
classDiagram
class Database {
+initialize(db_url) void
+create_tables() void
+create_process(process) ProcessModel
+create_alert(alert) AlertModel
+get_processes(limit,offset,search) ProcessModel[]
+get_alerts(limit,offset,severity,ack) AlertModel[]
+get_alert_stats() Dict
}
class Alert {
+id : int
+process_id : int
+rule_triggered : str
+severity : SeverityLevel
+risk_score : int
+timestamp : datetime
+acknowledged : bool
}
class ProcessEvent {
+id : int
+process_name : str
+parent_name : str
+command_line : str
+process_id : int
+parent_process_id : int
+timestamp : datetime
}
Database --> Alert : "stores"
Database --> ProcessEvent : "stores"
```

**Diagram sources**
- [backend/database/database.py:21-324](file://backend/database/database.py#L21-L324)
- [backend/models/alert.py:15-55](file://backend/models/alert.py#L15-L55)
- [backend/models/process.py:6-44](file://backend/models/process.py#L6-L44)

**Section sources**
- [backend/database/database.py:21-324](file://backend/database/database.py#L21-L324)
- [backend/models/alert.py:15-55](file://backend/models/alert.py#L15-L55)
- [backend/models/process.py:6-44](file://backend/models/process.py#L6-L44)

### Parser and Simulator
- Sysmon Parser: Supports EVTX, XML, and JSON event sources, normalizes to a unified event model.
- Log Simulator: Generates realistic normal and suspicious Sysmon events for testing and demos.

```mermaid
flowchart TD
Start(["Event Source"]) --> Detect["Detect Format<br/>EVTX/XML/JSON"]
Detect --> EVTX{"EVTX?"}
XML{"XML?"}
JSON{"JSON?"}
EVTX --> |Yes| ParseEVTX["Parse EVTX"]
EVTX --> |No| XML
XML --> |Yes| ParseXML["Parse XML"]
XML --> |No| JSON
JSON --> |Yes| ParseJSON["Parse JSON"]
JSON --> |No| Error["Unsupported Format"]
ParseEVTX --> Normalize["Normalize to SysmonEvent"]
ParseXML --> Normalize
ParseJSON --> Normalize
Normalize --> Output["Return Iterator of Events"]
```

**Diagram sources**
- [backend/parser/sysmon_parser.py:96-206](file://backend/parser/sysmon_parser.py#L96-L206)
- [backend/parser/sysmon_parser.py:208-327](file://backend/parser/sysmon_parser.py#L208-L327)

**Section sources**
- [backend/parser/sysmon_parser.py:61-385](file://backend/parser/sysmon_parser.py#L61-L385)
- [backend/parser/log_simulator.py:18-315](file://backend/parser/log_simulator.py#L18-L315)

### WebSocket Real-Time Streaming
- Connection Manager: Tracks active connections, broadcasts to all, and cleans up disconnected clients.
- Endpoints: /ws/alerts and /ws/events stream alerts and process events; clients receive heartbeats and can request stats.

```mermaid
sequenceDiagram
participant FE as "Frontend Client"
participant WS as "WebSocket Route"
participant CM as "ConnectionManager"
participant API as "FastAPI App"
FE->>WS : "Connect /ws/alerts"
WS->>CM : "connect(websocket)"
CM-->>FE : "connection accepted"
loop Live Updates
API->>CM : "broadcast_alert({type : 'alert',...})"
CM-->>FE : "JSON message"
API->>CM : "broadcast_event({type : 'process_event',...})"
CM-->>FE : "JSON message"
end
```

**Diagram sources**
- [backend/routes/websocket.py:68-167](file://backend/routes/websocket.py#L68-L167)
- [backend/routes/websocket.py:209-233](file://backend/routes/websocket.py#L209-L233)

**Section sources**
- [backend/routes/websocket.py:14-233](file://backend/routes/websocket.py#L14-L233)

### API Routes and Data Flows
- Alerts: Retrieve paginated alerts, recent alerts, stats, acknowledge/unacknowledge, bulk actions.
- Processes: Paginate, search, recent, stats, process tree, parent lookup, delete.
- Detection: CRUD rules, toggle, reload, test, stats, export/import.

```mermaid
sequenceDiagram
participant FE as "Frontend"
participant API as "FastAPI App"
participant Router as "Router"
participant DB as "Database"
FE->>API : "GET /api/alerts?limit=100"
API->>Router : "alerts_router"
Router->>DB : "get_alerts_async(limit,offset,filter)"
DB-->>Router : "List<AlertModel>"
Router-->>FE : "AlertResponse"
FE->>API : "GET /api/processes?limit=100"
API->>Router : "processes_router"
Router->>DB : "get_processes_async(limit,offset,search)"
DB-->>Router : "List<ProcessModel>"
Router-->>FE : "List<ProcessEvent>"
```

**Diagram sources**
- [backend/routes/alerts.py:18-54](file://backend/routes/alerts.py#L18-L54)
- [backend/routes/processes.py:19-42](file://backend/routes/processes.py#L19-L42)

**Section sources**
- [backend/routes/alerts.py:15-180](file://backend/routes/alerts.py#L15-L180)
- [backend/routes/processes.py:16-253](file://backend/routes/processes.py#L16-L253)
- [backend/routes/detection.py:14-256](file://backend/routes/detection.py#L14-L256)

## Dependency Analysis
- Backend modules depend on shared models and database abstractions.
- Detection engine depends on rules manager and database.
- Routes depend on database sessions and detection engine.
- Frontend depends on API client and WebSocket hook.

```mermaid
graph LR
FE["frontend/src/*"] --> API["backend/main.py"]
API --> ROUTERS["routes/*.py"]
ROUTERS --> DB["database/database.py"]
ROUTERS --> DET["detection/engine.py"]
DET --> RULES["detection/rules.py"]
DET --> MODELS["models/*.py"]
API --> PARSER["parser/sysmon_parser.py"]
API --> SIM["parser/log_simulator.py"]
API --> WS["routes/websocket.py"]
```

**Diagram sources**
- [backend/main.py:171-192](file://backend/main.py#L171-L192)
- [backend/database/database.py:21-70](file://backend/database/database.py#L21-L70)
- [backend/detection/engine.py:64-82](file://backend/detection/engine.py#L64-L82)
- [backend/detection/rules.py:273-313](file://backend/detection/rules.py#L273-L313)
- [backend/parser/sysmon_parser.py:61-95](file://backend/parser/sysmon_parser.py#L61-L95)
- [backend/parser/log_simulator.py:18-37](file://backend/parser/log_simulator.py#L18-L37)
- [backend/routes/websocket.py:14-65](file://backend/routes/websocket.py#L14-L65)
- [frontend/src/api/client.ts:1-124](file://frontend/src/api/client.ts#L1-L124)
- [frontend/src/hooks/useWebSocket.ts:1-103](file://frontend/src/hooks/useWebSocket.ts#L1-L103)

**Section sources**
- [backend/main.py:171-192](file://backend/main.py#L171-L192)
- [backend/database/database.py:21-70](file://backend/database/database.py#L21-L70)
- [backend/detection/engine.py:64-82](file://backend/detection/engine.py#L64-L82)
- [backend/detection/rules.py:273-313](file://backend/detection/rules.py#L273-L313)
- [backend/parser/sysmon_parser.py:61-95](file://backend/parser/sysmon_parser.py#L61-L95)
- [backend/parser/log_simulator.py:18-37](file://backend/parser/log_simulator.py#L18-L37)
- [backend/routes/websocket.py:14-65](file://backend/routes/websocket.py#L14-L65)
- [frontend/src/api/client.ts:1-124](file://frontend/src/api/client.ts#L1-L124)
- [frontend/src/hooks/useWebSocket.ts:1-103](file://frontend/src/hooks/useWebSocket.ts#L1-L103)

## Performance Considerations
- SQLite choice: Lightweight, embedded storage suitable for small to medium deployments; consider WAL mode and pragmas for tuning.
- Asynchronous I/O: Async database sessions reduce blocking during concurrent requests.
- Rule evaluation: Regex compilation is cached per rule; avoid excessive rule churn to minimize overhead.
- Frequency tracking: Thread-safe deque-based tracker limits memory and provides O(1) window maintenance.
- WebSocket broadcasting: Batch and throttle updates; implement client-side debouncing.
- CORS and middleware: Ensure minimal latency; avoid permissive wildcard in production.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- Health checks: Use the /health endpoint to verify database connectivity and engine status.
- Logging: Application logs to stdout and file; inspect logs directory for errors.
- WebSocket issues: Verify protocol (ws/wss), reconnection attempts, and heartbeat handling.
- API errors: Check router responses for 404/400 statuses and payload validation failures.
- Data cleanup: Use retention policies to prune old alerts and processes.

**Section sources**
- [backend/main.py:214-223](file://backend/main.py#L214-L223)
- [backend/main.py:226-240](file://backend/main.py#L226-L240)
- [backend/routes/websocket.py:68-167](file://backend/routes/websocket.py#L68-L167)

## Conclusion
EDR Lite integrates a FastAPI backend with a React frontend to deliver real-time endpoint visibility. Its layered design separates concerns cleanly, enabling modular development and straightforward scaling. SQLite provides a pragmatic persistence layer, while JSON-based detection rules offer flexibility and ease of management. WebSocket endpoints ensure timely alert delivery to the dashboard. With careful attention to monitoring, security, and performance, the system can serve as a foundation for lightweight EDR deployments.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Infrastructure Requirements and Deployment Options
- Runtime: Python 3.10+, Node.js for frontend build.
- Backend: Uvicorn/ASGI server; configure host/port via environment variables.
- Database: SQLite file; ensure write permissions and disk space.
- Frontend: Build artifacts served by FastAPI static files mount or external CDN.
- Deployment topologies:
  - Single VM: Run FastAPI with Uvicorn and serve static assets.
  - Containerized: Dockerize backend; expose port; mount SQLite volume.
  - Reverse proxy: Nginx/Apache in front of Uvicorn; terminate TLS.

[No sources needed since this section provides general guidance]

### Security Considerations
- CORS: Configure origins explicitly; avoid wildcards in production.
- Authentication/Authorization: Not implemented; consider adding middleware or gateway protection.
- Input validation: Pydantic models enforce schema; sanitize logs and avoid exposing internals.
- Secrets: Environment variables for configuration; avoid committing secrets.

[No sources needed since this section provides general guidance]

### Monitoring and Observability
- Logging: Structured logs to file and stdout; integrate with log aggregation systems.
- Metrics: Expose Prometheus-compatible metrics or use application-level counters.
- Tracing: Add OpenTelemetry instrumentation for request tracing.

[No sources needed since this section provides general guidance]