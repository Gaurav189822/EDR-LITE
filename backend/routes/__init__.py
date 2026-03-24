from .alerts import router as alerts_router
from .processes import router as processes_router
from .detection import router as detection_router
from .websocket import router as websocket_router

__all__ = ["alerts_router", "processes_router", "detection_router", "websocket_router"]