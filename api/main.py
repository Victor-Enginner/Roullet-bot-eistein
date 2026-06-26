from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from typing import List, Dict, Any
from datetime import datetime
import uvicorn

from core.monitor import GameMonitor
from signals.engine import SignalEngine
from storage.database import Database
from analytics.metrics import Metrics
from config.settings import Settings

app = FastAPI(
    title="Skynet Signal Platform",
    description="Real-time Roulette Signal Intelligence Platform",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global instances
monitor = None
signal_engine = None
db = None
metrics = None

@app.on_event("startup")
async def startup_event():
    global monitor, signal_engine, db, metrics

    db = Database(str(Settings.DB_PATH))
    metrics = Metrics(start_time=datetime.now().timestamp())

    # Initialize signal engine
    from signals.engine import SignalEngine
    signal_engine = SignalEngine(db)

    # Initialize monitor (optional - can be started separately)
    # monitor = GameMonitor()

@app.on_event("shutdown")
async def shutdown_event():
    if monitor:
        monitor.stop()

# Auth dependency (placeholder)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # TODO: Implement proper JWT validation
    return {"user_id": 1, "plan": "premium"}

# WebSocket connections for realtime signals
active_connections: List[WebSocket] = []

@app.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"status": "connected"}))
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)

async def broadcast_signal(signal_data: Dict[str, Any]):
    """Broadcast signal to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps(signal_data))
        except Exception as e:
            print(f"Broadcast error: {e}")
            active_connections.remove(connection)

# REST API Endpoints

@app.get("/api/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime": metrics.uptime_seconds() if metrics else 0,
        "monitor_active": monitor is not None and monitor._active if monitor else False
    }

@app.get("/api/signals/recent")
async def get_recent_signals(limit: int = 10, user=Depends(get_current_user)):
    """Get recent signals"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    signals = db.get_recent_signals(limit)
    return {"signals": signals}

@app.get("/api/numbers/recent")
async def get_recent_numbers(limit: int = 50, user=Depends(get_current_user)):
    """Get recent numbers"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    numbers = db.get_recent_numbers(limit)
    return {"numbers": numbers}

@app.get("/api/statistics")
async def get_statistics(user=Depends(get_current_user)):
    """Get system statistics"""
    if not db:
        raise HTTPException(status_code=500, detail="Database not available")

    stats = db.get_statistics()
    return stats

@app.post("/api/monitor/start")
async def start_monitor(user=Depends(get_current_user)):
    """Start the game monitor"""
    global monitor

    if monitor and monitor._active:
        return {"status": "already_running"}

    try:
        monitor = GameMonitor()
        success = monitor.start()
        if success:
            return {"status": "started"}
        else:
            raise HTTPException(status_code=500, detail="Failed to start monitor")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitor start error: {str(e)}")

@app.post("/api/monitor/stop")
async def stop_monitor(user=Depends(get_current_user)):
    """Stop the game monitor"""
    global monitor

    if monitor:
        monitor.stop()
        monitor = None

    return {"status": "stopped"}

@app.get("/api/metrics")
async def get_metrics(user=Depends(get_current_user)):
    """Get system metrics"""
    if not metrics:
        raise HTTPException(status_code=500, detail="Metrics not available")

    return {
        "uptime_seconds": metrics.uptime_seconds(),
        "numbers_detected": metrics.numbers_detected,
        "errors_count": metrics.errors_count,
        "last_number_time": metrics.last_number_time
    }

# Signal processing endpoint (for manual testing)
@app.post("/api/signals/process")
async def process_signal(number: int, user=Depends(get_current_user)):
    """Process a number and generate signal"""
    if not signal_engine:
        raise HTTPException(status_code=500, detail="Signal engine not available")

    try:
        signal = signal_engine.process_number(number)

        if signal:
            # Broadcast to WebSocket clients
            await broadcast_signal(signal)

        return {"signal": signal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signal processing error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )