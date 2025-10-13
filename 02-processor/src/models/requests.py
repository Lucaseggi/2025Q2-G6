from pydantic import BaseModel, Field


class ReplayRequest(BaseModel):
    """Request to replay a specific norm from cache"""
    infoleg_id: int = Field(..., description="InfoLeg norm ID to replay")
    force: bool = Field(default=False, description="Force reprocessing even if not in cache")
