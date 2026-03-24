"""
EDR Lite - Main Application

FastAPI application for the EDR Lite Endpoint Detection and Response system.
Provides REST API endpoints and WebSocket support for real-time monitoring.
"""

import os
import sys
import json
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/edr_lite.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Import application modules
from database import init_db, Database
from detection import DetectionEngine
from parser import LogSimulator, SysmonParser
from routes import alerts_router, processes_router, detection_router, websocket_router
from routes.websocket import broadcast_alert, broadcast_event, broadcast_stats


# Global instances
db: Optional[Database] = None
detection_engine: Optional[DetectionEngine] = None
log_simulator: Optional[LogSimulator] = None
monitoring_task: Optional[asyncio.Task] = None


class EDRConfig:
    """Application configuration"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edr_lite.db")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"
    SIMULATION_INTERVAL = float(os.getenv("SIMULATION_INTERVAL", "5.0"))  # seconds
    AUTO_INGEST = os.getenv("AUTO_INGEST", "true").lower() == "true"


async def simulate_sysmon_events():
    """Background task to simulate Sysmon events"""
    global log_simulator, detection_engine
    
    logger.info("Starting Sysmon event simulation")
    
    while True:
        try:
            if log_simulator and detection_engine:
                # Generate a simulated event
                event_data = log_simulator.generate_event()
                
                # Convert to ProcessCreate model
                from models import ProcessCreate
                
                event_data_inner = event_data.get("EventData", {})
                process = ProcessCreate(
                    process_name=event_data_inner.get("Image", "unknown"),
                    parent_name=event_data_inner.get("ParentImage", "unknown"),
                    command_line=event_data_inner.get("CommandLine", ""),
                    process_id=int(event_data_inner.get("ProcessId", 0)),
                    parent_process_id=int(event_data_inner.get("ParentProcessId", 0)),
                    timestamp=datetime.utcnow(),
                    user=event_data_inner.get("User"),
                    computer=event_data.get("Computer")
                )
                
                # Process and create alerts
                process_id, alerts = detection_engine.process_and_alert(process)
                
                # Broadcast to WebSocket clients
                await broadcast_event({
                    "id": process_id,
                    "process_name": process.process_name,
                    "parent_name": process.parent_name,
                    "command_line": process.command_line,
                    "timestamp": process.timestamp.isoformat()
                })
                
                # Broadcast alerts
                for alert in alerts:
                    await broadcast_alert({
                        "process_id": alert.process_id,
                        "rule_triggered": alert.rule_triggered,
                        "severity": alert.severity,
                        "description": alert.description,
                        "risk_score": alert.risk_score,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                if alerts:
                    logger.info(f"Generated {len(alerts)} alerts from simulated event")
            
            await asyncio.sleep(EDRConfig.SIMULATION_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in simulation task: {e}")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db, detection_engine, log_simulator, monitoring_task
    
    # Startup
    logger.info("=" * 60)
    logger.info("EDR Lite - Starting up")
    logger.info("=" * 60)
    
    # Initialize database
    logger.info("Initializing database...")
    init_db(EDRConfig.DATABASE_URL)
    db = Database()
    db.initialize(EDRConfig.DATABASE_URL)
    
    # Initialize detection engine
    logger.info("Initializing detection engine...")
    detection_engine = DetectionEngine(db)
    
    # Initialize log simulator if in simulation mode
    if EDRConfig.SIMULATION_MODE:
        logger.info("Initializing log simulator...")
        log_simulator = LogSimulator()
        logger.info(f"Simulation mode: ENABLED (interval: {EDRConfig.SIMULATION_INTERVAL}s)")
    
    # Start background monitoring task
    if EDRConfig.AUTO_INGEST and EDRConfig.SIMULATION_MODE:
        logger.info("Starting background monitoring task...")
        monitoring_task = asyncio.create_task(simulate_sysmon_events())
    
    logger.info("EDR Lite startup complete")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("EDR Lite - Shutting down")
    logger.info("=" * 60)
    
    if monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="EDR Lite - Endpoint Detection and Response",
    description="Real-time endpoint monitoring and threat detection system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=EDRConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(alerts_router)
app.include_router(processes_router)
app.include_router(detection_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "EDR Lite",
        "version": "1.0.0",
        "description": "Endpoint Detection and Response System",
        "status": "running",
        "endpoints": {
            "api_docs": "/docs",
            "alerts": "/api/alerts",
            "processes": "/api/processes",
            "detection": "/api/detection",
            "websocket_alerts": "/ws/alerts",
            "websocket_events": "/ws/events"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db else "disconnected",
        "detection_engine": "running" if detection_engine else "stopped",
        "simulation_mode": EDRConfig.SIMULATION_MODE
    }


@app.get("/api/stats")
async def get_system_stats():
    """Get overall system statistics"""
    if not detection_engine:
        return {"error": "Detection engine not initialized"}
    
    engine_stats = detection_engine.get_statistics()
    rule_stats = detection_engine.rule_manager.get_rule_stats()
    
    return {
        "engine": engine_stats,
        "rules": rule_stats,
        "simulation_mode": EDRConfig.SIMULATION_MODE,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/ingest")
async def ingest_event(event_data: dict):
    """
    Manually ingest a Sysmon event.
    
    Expected format:
    {
        "EventID": 1,
        "Computer": "WORKSTATION-001",
        "EventData": {
            "Image": "C:\\Windows\\System32\\cmd.exe",
            "ParentImage": "C:\\Windows\\explorer.exe",
            "CommandLine": "cmd.exe /c whoami",
            "ProcessId": "1234",
            "ParentProcessId": "5678",
            ...
        }
    }
    """
    from models import ProcessCreate
    
    try:
        event_data_inner = event_data.get("EventData", {})
        
        process = ProcessCreate(
            process_name=event_data_inner.get("Image", "unknown"),
            parent_name=event_data_inner.get("ParentImage", "unknown"),
            command_line=event_data_inner.get("CommandLine", ""),
            process_id=int(event_data_inner.get("ProcessId", 0)),
            parent_process_id=int(event_data_inner.get("ParentProcessId", 0)),
            timestamp=datetime.utcnow(),
            user=event_data_inner.get("User"),
            computer=event_data.get("Computer")
        )
        
        # Process and create alerts
        process_id, alerts = detection_engine.process_and_alert(process)
        
        # Broadcast to WebSocket clients
        await broadcast_event({
            "id": process_id,
            "process_name": process.process_name,
            "parent_name": process.parent_name,
            "command_line": process.command_line,
            "timestamp": process.timestamp.isoformat()
        })
        
        # Broadcast alerts
        for alert in alerts:
            await broadcast_alert({
                "process_id": alert.process_id,
                "rule_triggered": alert.rule_triggered,
                "severity": alert.severity,
                "description": alert.description,
                "risk_score": alert.risk_score,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return {
            "status": "success",
            "process_id": process_id,
            "alerts_generated": len(alerts),
            "is_threat": len(alerts) > 0
        }
        
    except Exception as e:
        logger.error(f"Error ingesting event: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/simulate/batch")
async def simulate_batch(count: int = 10, suspicious_ratio: float = 0.2):
    """Generate a batch of simulated events"""
    if not log_simulator:
        return {"error": "Simulator not initialized"}
    
    events = log_simulator.generate_batch(count, suspicious_ratio)
    
    # Ingest each event
    ingested = 0
    alerts_total = 0
    
    for event_data in events:
        result = await ingest_event(event_data)
        if result.get("status") == "success":
            ingested += 1
            alerts_total += result.get("alerts_generated", 0)
    
    return {
        "status": "success",
        "events_generated": len(events),
        "events_ingested": ingested,
        "alerts_generated": alerts_total
    }


@app.post("/api/simulation/toggle")
async def toggle_simulation(enabled: bool):
    """Enable or disable simulation mode"""
    global monitoring_task
    
    EDRConfig.SIMULATION_MODE = enabled
    
    if enabled and not monitoring_task:
        monitoring_task = asyncio.create_task(simulate_sysmon_events())
        return {"status": "success", "message": "Simulation enabled"}
    elif not enabled and monitoring_task:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass
        monitoring_task = None
        return {"status": "success", "message": "Simulation disabled"}
    
    return {"status": "success", "message": f"Simulation already {'enabled' if enabled else 'disabled'}"}


# Serve static files (frontend build)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EDR Lite Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: #0f172a;
                color: #e2e8f0;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: #38bdf8;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #94a3b8;
                margin-bottom: 30px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #1e293b;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #334155;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #38bdf8;
            }
            .stat-label {
                color: #94a3b8;
                font-size: 0.9em;
            }
            .section {
                background: #1e293b;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                border: 1px solid #334155;
            }
            .section h2 {
                margin-top: 0;
                color: #38bdf8;
                border-bottom: 1px solid #334155;
                padding-bottom: 10px;
            }
            .alert-item {
                padding: 15px;
                margin: 10px 0;
                border-radius: 6px;
                border-left: 4px solid;
            }
            .alert-critical { background: #450a0a; border-color: #ef4444; }
            .alert-high { background: #451a03; border-color: #f97316; }
            .alert-medium { background: #422006; border-color: #eab308; }
            .alert-low { background: #0f172a; border-color: #22c55e; }
            .severity-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
                text-transform: uppercase;
            }
            .severity-critical { background: #ef4444; color: white; }
            .severity-high { background: #f97316; color: white; }
            .severity-medium { background: #eab308; color: black; }
            .severity-low { background: #22c55e; color: white; }
            .process-item {
                padding: 10px;
                margin: 5px 0;
                background: #0f172a;
                border-radius: 4px;
                font-family: monospace;
                font-size: 0.9em;
            }
            .process-name { color: #38bdf8; }
            .parent-name { color: #94a3b8; }
            .command-line { color: #cbd5e1; margin-top: 5px; }
            .timestamp { color: #64748b; font-size: 0.8em; }
            .status-connected { color: #22c55e; }
            .status-disconnected { color: #ef4444; }
            #connection-status {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 10px 20px;
                background: #1e293b;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            .refresh-btn {
                background: #38bdf8;
                color: #0f172a;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-weight: bold;
            }
            .refresh-btn:hover { background: #7dd3fc; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>EDR Lite Dashboard</h1>
            <p class="subtitle">Real-time Endpoint Detection and Response</p>
            
            <div id="connection-status">
                WebSocket: <span id="ws-status" class="status-disconnected">Disconnected</span>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="total-alerts">-</div>
                    <div class="stat-label">Total Alerts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="high-severity">-</div>
                    <div class="stat-label">High Severity</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-processes">-</div>
                    <div class="stat-label">Processes Monitored</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="rules-active">-</div>
                    <div class="stat-label">Active Rules</div>
                </div>
            </div>
            
            <div class="section">
                <h2>Live Alerts</h2>
                <button class="refresh-btn" onclick="loadAlerts()">Refresh</button>
                <div id="alerts-container">
                    <p>Loading alerts...</p>
                </div>
            </div>
            
            <div class="section">
                <h2>Recent Processes</h2>
                <button class="refresh-btn" onclick="loadProcesses()">Refresh</button>
                <div id="processes-container">
                    <p>Loading processes...</p>
                </div>
            </div>
        </div>
        
        <script>
            const API_BASE = '';
            let ws = null;
            
            // Connect to WebSocket
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws/alerts`);
                
                ws.onopen = () => {
                    document.getElementById('ws-status').textContent = 'Connected';
                    document.getElementById('ws-status').className = 'status-connected';
                };
                
                ws.onclose = () => {
                    document.getElementById('ws-status').textContent = 'Disconnected';
                    document.getElementById('ws-status').className = 'status-disconnected';
                    // Reconnect after 5 seconds
                    setTimeout(connectWebSocket, 5000);
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'alert') {
                        prependAlert(data.data);
                    } else if (data.type === 'process_event') {
                        prependProcess(data.data);
                    }
                };
            }
            
            // Load alerts from API
            async function loadAlerts() {
                try {
                    const response = await fetch(`${API_BASE}/api/alerts?limit=10`);
                    const data = await response.json();
                    
                    const container = document.getElementById('alerts-container');
                    if (data.alerts.length === 0) {
                        container.innerHTML = '<p>No alerts found</p>';
                        return;
                    }
                    
                    container.innerHTML = data.alerts.map(alert => `
                        <div class="alert-item alert-${alert.severity}">
                            <span class="severity-badge severity-${alert.severity}">${alert.severity}</span>
                            <strong>${alert.rule_triggered}</strong>
                            <p>${alert.description}</p>
                            <div class="timestamp">${new Date(alert.timestamp).toLocaleString()}</div>
                        </div>
                    `).join('');
                    
                    document.getElementById('total-alerts').textContent = data.total;
                    document.getElementById('high-severity').textContent = 
                        (data.severity_counts.high || 0) + (data.severity_counts.critical || 0);
                } catch (error) {
                    console.error('Error loading alerts:', error);
                }
            }
            
            // Load processes from API
            async function loadProcesses() {
                try {
                    const response = await fetch(`${API_BASE}/api/processes?limit=10`);
                    const data = await response.json();
                    
                    const container = document.getElementById('processes-container');
                    if (data.length === 0) {
                        container.innerHTML = '<p>No processes found</p>';
                        return;
                    }
                    
                    container.innerHTML = data.map(proc => `
                        <div class="process-item">
                            <span class="process-name">${proc.process_name}</span>
                            <span class="parent-name">← ${proc.parent_name}</span>
                            <div class="command-line">${proc.command_line}</div>
                            <div class="timestamp">${new Date(proc.timestamp).toLocaleString()}</div>
                        </div>
                    `).join('');
                    
                    document.getElementById('total-processes').textContent = data.length;
                } catch (error) {
                    console.error('Error loading processes:', error);
                }
            }
            
            // Load stats
            async function loadStats() {
                try {
                    const response = await fetch(`${API_BASE}/api/stats`);
                    const data = await response.json();
                    
                    if (data.rules) {
                        document.getElementById('rules-active').textContent = 
                            data.rules.enabled_rules;
                    }
                } catch (error) {
                    console.error('Error loading stats:', error);
                }
            }
            
            // Prepend new alert to list
            function prependAlert(alert) {
                const container = document.getElementById('alerts-container');
                const div = document.createElement('div');
                div.className = `alert-item alert-${alert.severity}`;
                div.innerHTML = `
                    <span class="severity-badge severity-${alert.severity}">${alert.severity}</span>
                    <strong>${alert.rule_triggered}</strong>
                    <p>${alert.description}</p>
                    <div class="timestamp">${new Date(alert.timestamp).toLocaleString()}</div>
                `;
                container.insertBefore(div, container.firstChild);
                
                // Remove old alerts if too many
                while (container.children.length > 20) {
                    container.removeChild(container.lastChild);
                }
            }
            
            // Prepend new process to list
            function prependProcess(proc) {
                const container = document.getElementById('processes-container');
                const div = document.createElement('div');
                div.className = 'process-item';
                div.innerHTML = `
                    <span class="process-name">${proc.process_name}</span>
                    <span class="parent-name">← ${proc.parent_name}</span>
                    <div class="command-line">${proc.command_line}</div>
                    <div class="timestamp">${new Date(proc.timestamp).toLocaleString()}</div>
                `;
                container.insertBefore(div, container.firstChild);
                
                while (container.children.length > 20) {
                    container.removeChild(container.lastChild);
                }
            }
            
            // Initialize
            connectWebSocket();
            loadAlerts();
            loadProcesses();
            loadStats();
            
            // Refresh every 30 seconds
            setInterval(() => {
                loadAlerts();
                loadProcesses();
                loadStats();
            }, 30000);
        </script>
    </body>
    </html>
    """
    return html_content


if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting EDR Lite server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )