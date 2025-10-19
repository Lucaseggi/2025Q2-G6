from pydantic import BaseModel, Field
from typing import Literal, Dict, Any, List
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response model"""
    status: Literal["healthy"] = "healthy"
    service: str = "enhanced-scraper-ms"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScrapeResponse(BaseModel):
    """Response model for scrape operations"""
    status: Literal["success", "cached", "error"]
    message: str
    infoleg_id: int
    source: str = Field(description="Source of the data: 'cache', 'scraped', or error reason")
    cache_hit: bool = Field(description="Whether data was served from cache")
    forced: bool = Field(description="Whether force parameter was used")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Successfully scraped norm 183532",
                "infoleg_id": 183532,
                "source": "scraped",
                "cache_hit": False,
                "forced": False,
                "timestamp": "2024-01-15T10:30:00"
            }
        }
    }


class ProcessResponse(BaseModel):
    """Response model for process operations"""
    status: Literal["success", "cached", "error"]
    message: str
    infoleg_id: int
    source: str = Field(description="Source of the data: 'cache', 'scraped', or error reason")
    cache_hit: bool = Field(description="Whether data was served from cache")
    forced: bool = Field(description="Whether force parameter was used")
    action: Literal["process"] = "process"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Successfully processed norm 183532",
                "infoleg_id": 183532,
                "source": "scraped",
                "cache_hit": False,
                "forced": True,
                "action": "process",
                "timestamp": "2024-01-15T10:30:00"
            }
        }
    }


class ReplayResponse(BaseModel):
    """Response model for replay operations"""
    status: Literal["success", "error"]
    message: str
    infoleg_id: int
    cache_hit: bool = Field(description="Whether data was found in cache")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Successfully replayed norm 183532 to purifying queue",
                "infoleg_id": 183532,
                "cache_hit": True,
                "timestamp": "2024-01-15T10:30:00"
            }
        }
    }


class DailyScrapeResponse(BaseModel):
    """Response model for daily scrape operations"""
    status: Literal["success", "error"]
    message: str
    stats: Dict[str, Any] = Field(description="Statistics about the scraping operation")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Daily scrape completed for 2025-10-15: 46 scraped, 0 from cache, 0 failed",
                "stats": {
                    "target_date": "2025-10-15",
                    "total_norms": 46,
                    "scraped": 46,
                    "cached": 0,
                    "failed": 0
                },
                "timestamp": "2024-01-15T10:30:00"
            }
        }
    }


class DateRangeScrapeResponse(BaseModel):
    """Response model for date range scrape operations"""
    status: Literal["success", "error"]
    message: str
    daily_stats: List[Dict[str, Any]] = Field(description="Statistics for each day in the range")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Date range scrape completed (2025-10-01 to 2025-10-15): 500 total norms, 450 scraped, 50 from cache, 0 failed",
                "daily_stats": [
                    {
                        "target_date": "2025-10-01",
                        "total_norms": 30,
                        "scraped": 25,
                        "cached": 5,
                        "failed": 0
                    }
                ],
                "timestamp": "2024-01-15T10:30:00"
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response model"""
    status: Literal["error"] = "error"
    message: str
    action: str = Field(default="", description="Action that was being performed")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())