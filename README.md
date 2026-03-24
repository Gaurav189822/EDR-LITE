# EDR Lite - Kernel-Level Process Monitoring System

A real-time endpoint monitoring and threat detection system using Windows Sysmon logs. The system detects suspicious process behaviors using a rule-based detection engine and displays alerts via a modern web dashboard.

## Features

- **Real-time Process Monitoring**: Monitors Windows Sysmon Event ID 1 (Process Creation) events
- **Rule-Based Detection Engine**: JSON-driven detection rules for various attack patterns
- **WebSocket Support**: Live streaming of alerts and process events
- **Modern React Dashboard**: Dark-themed, responsive UI with real-time updates
- **REST API**: Complete API for alerts, processes, and detection rules
- **SQLite Database**: Lightweight, serverless database for events and alerts
- **Simulation Mode**: Built-in event simulator for testing and demonstration

## Detection Capabilities

### Parent-Child Anomaly Detection
- Office applications spawning shells (Outlook → cmd.exe)
- Browsers spawning scripting engines
- System processes spawning suspicious children

### Command Line Analysis
- Encoded PowerShell commands
- Download cradles and remote execution
- LOLBAS technique detection

### Frequency Analysis
- Rapid process spawning detection
- Threshold-based anomaly detection

## Architecture

```
EDR LITE/
├── backend/                 # FastAPI Backend
│   ├── main.py             # Application entry point
│   ├── models/             # Pydantic models
│   ├── database/           # SQLAlchemy database layer
│   ├── parser/             # Sysmon log parser
│   ├── detection/          # Detection engine & rules
│   ├── routes/             # API routes
│   └── config/             # Configuration files
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom hooks
│   │   └── api/            # API client
│   └── package.json
└── sample_data/            # Sample Sysmon events
```

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- pip
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
cp .env.example .env
```

5. Run the server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

### Access the Dashboard

Once both servers are running:

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Built-in Dashboard**: http://localhost:8000/dashboard

## API Endpoints

### Alerts
- `GET /api/alerts` - List alerts with filtering
- `GET /api/alerts/{id}` - Get specific alert
- `POST /api/alerts/{id}/acknowledge` - Acknowledge alert
- `GET /api/alerts/stats` - Alert statistics

### Processes
- `GET /api/processes` - List process events
- `GET /api/processes/{id}` - Get specific process
- `GET /api/processes/{id}/tree` - Get process tree

### Detection
- `GET /api/detection/rules` - List detection rules
- `POST /api/detection/rules` - Create new rule
- `POST /api/detection/test` - Test process against rules
- `POST /api/detection/reload` - Reload rules from files

### WebSocket
- `ws://localhost:8000/ws/alerts` - Real-time alerts stream
- `ws://localhost:8000/ws/events` - Real-time events stream

## Detection Rules

Rules are defined in JSON format and support multiple types:

### Parent-Child Rule
```json
{
  "id": "RULE-001",
  "name": "Outlook Spawning Shell",
  "rule_type": "parent_child",
  "description": "Email client spawning command shell",
  "severity": "high",
  "enabled": true,
  "parent_process": "outlook\\.exe",
  "child_process": "cmd\\.exe|powershell\\.exe",
  "risk_score": 80
}
```

### Command Line Rule
```json
{
  "id": "RULE-007",
  "name": "Encoded PowerShell",
  "rule_type": "command_line",
  "description": "PowerShell with encoded command",
  "severity": "high",
  "enabled": true,
  "child_process": "powershell\\.exe",
  "command_line_contains": ["-enc", "-encodedcommand"],
  "risk_score": 85
}
```

### Frequency Rule
```json
{
  "id": "RULE-017",
  "name": "Rapid Process Spawning",
  "rule_type": "frequency",
  "description": "High rate of process creation",
  "severity": "medium",
  "enabled": true,
  "max_events_per_minute": 30,
  "time_window_minutes": 1,
  "risk_score": 60
}
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///./edr_lite.db` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `SIMULATION_MODE` | Enable event simulation | `true` |
| `SIMULATION_INTERVAL` | Seconds between events | `5.0` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |

## Production Deployment

### Backend

1. Set `DEBUG=false` in `.env`
2. Use a production ASGI server:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend

Build for production:
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`. Serve these with a static file server or copy to the backend's `static/` directory.

## Testing

### Simulate Events

Use the built-in simulator:
```bash
curl -X POST "http://localhost:8000/api/simulate/batch?count=10&suspicious_ratio=0.3"
```

### Test Detection Rules

Test a process against all rules:
```bash
curl -X POST "http://localhost:8000/api/detection/test" \
  -H "Content-Type: application/json" \
  -d '{
    "process_name": "cmd.exe",
    "parent_name": "outlook.exe",
    "command_line": "cmd.exe /c whoami"
  }'
```

### Import Sample Data

```bash
curl -X POST "http://localhost:8000/api/ingest" \
  -H "Content-Type: application/json" \
  -d @sample_data/sample_sysmon_events.json
```

## Default Detection Rules

The system includes 20+ pre-configured detection rules covering:

1. **Office Macro Threats**: Word/Excel spawning PowerShell
2. **Email Phishing**: Outlook spawning shells
3. **Browser Exploits**: Chrome/Firefox spawning cmd.exe
4. **Credential Dumping**: LSASS spawning suspicious processes
5. **Ransomware Indicators**: Shadow copy deletion
6. **LOLBAS Techniques**: CertUtil, Regsvr32, MSHTA abuse
7. **Persistence**: Startup folder execution
8. **Encoded Commands**: Base64 PowerShell detection

## Project Structure Details

### Backend Components

- **Parser** (`parser/`): Handles Sysmon EVTX, XML, and JSON formats
- **Detection Engine** (`detection/`): Rule matching and threat scoring
- **Database** (`database/`): SQLAlchemy models and async queries
- **Routes** (`routes/`): FastAPI endpoints for REST and WebSocket

### Frontend Components

- **Dashboard**: Overview with stats and recent activity
- **Alerts**: Alert management with filtering and bulk actions
- **Processes**: Process event browser with search
- **Detection Rules**: Rule management and testing interface

## Security Considerations

- This is a demonstration/proof-of-concept system
- Not intended for production security monitoring without additional hardening
- Use proper authentication/authorization for production deployments
- Consider using a production database (PostgreSQL) for high-volume deployments
- Enable HTTPS for production deployments

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style patterns
- Tests are included for new features
- Documentation is updated
- Commit messages are clear and descriptive

## Acknowledgments

- Microsoft Sysmon for the excellent event logging
- FastAPI for the high-performance Python web framework
- React and Tailwind CSS for the modern frontend stack