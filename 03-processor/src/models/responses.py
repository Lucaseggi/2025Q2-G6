from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    service: str = "processor-ms"


class ReplayResponse(BaseModel):
    """Replay operation response"""
    status: str
    message: str
    infoleg_id: int
    cache_hit: bool = False


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    message: str
