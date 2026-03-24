"""
WebSocket Routes

Real-time streaming of alerts and process events via WebSockets.
"""

import asyncio
import json
import logging
from typing import Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")
            self.disconnect(websocket)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/alerts")
async def alerts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts.
    
    Clients will receive:
    - New alerts as they are generated
    - Periodic heartbeat messages
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await manager.send_to_client(websocket, {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to EDR Lite alert stream"
        })
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for messages from client (with timeout)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle client messages
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    await manager.send_to_client(websocket, {
                        "type": "error",
                        "message": "Invalid JSON received"
                    })
                    
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await manager.send_to_client(websocket, {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/events")
async def events_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time process events.
    
    Clients will receive:
    - New process events as they are ingested
    - Periodic statistics updates
    """
    await manager.connect(websocket)
    
    try:
        await manager.send_to_client(websocket, {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to EDR Lite event stream"
        })
        
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    await manager.send_to_client(websocket, {
                        "type": "error",
                        "message": "Invalid JSON received"
                    })
                    
            except asyncio.TimeoutError:
                await manager.send_to_client(websocket, {
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message: dict):
    """Handle messages from WebSocket clients"""
    msg_type = message.get("type", "unknown")
    
    if msg_type == "ping":
        await manager.send_to_client(websocket, {
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif msg_type == "subscribe":
        channel = message.get("channel", "all")
        await manager.send_to_client(websocket, {
            "type": "subscribed",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    elif msg_type == "get_stats":
        # Send current statistics
        from detection import DetectionEngine
        from database import Database
        
        db = Database()
        engine = DetectionEngine(db)
        stats = engine.get_statistics()
        
        await manager.send_to_client(websocket, {
            "type": "stats",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    else:
        await manager.send_to_client(websocket, {
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        })


async def broadcast_alert(alert_data: dict):
    """Broadcast a new alert to all connected clients"""
    await manager.broadcast({
        "type": "alert",
        "data": alert_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_event(event_data: dict):
    """Broadcast a new process event to all connected clients"""
    await manager.broadcast({
        "type": "process_event",
        "data": event_data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_stats(stats_data: dict):
    """Broadcast statistics update to all connected clients"""
    await manager.broadcast({
        "type": "stats_update",
        "data": stats_data,
        "timestamp": datetime.utcnow().isoformat()
    })