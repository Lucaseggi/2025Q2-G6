from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


class ScrapeRequest(BaseModel):
    """Request model for scraping a norm"""
    infoleg_id: int = Field(gt=0, description="Positive integer norm ID to scrape")
    force: bool = Field(default=False, description="Force fresh scraping, bypass cache")

    model_config = {
        "json_schema_extra": {
            "example": {
                "infoleg_id": 183532,
                "force": False
            }
        }
    }


class ProcessRequest(BaseModel):
    """Request model for processing a norm"""
    infoleg_id: int = Field(gt=0, description="Positive integer norm ID to process")
    force: bool = Field(default=False, description="Force fresh processing, bypass cache")

    model_config = {
        "json_schema_extra": {
            "example": {
                "infoleg_id": 183532,
                "force": False
            }
        }
    }


class ReplayRequest(BaseModel):
    """Request model for replaying a norm from cache"""
    infoleg_id: int = Field(gt=0, description="Positive integer norm ID to replay from cache")
    force: bool = Field(default=False, description="Force replay even if already in queue")

    model_config = {
        "json_schema_extra": {
            "example": {
                "infoleg_id": 183532,
                "force": False
            }
        }
    }

class DailyScrapeRequest(BaseModel):
    """Request model for daily scraping"""
    target_date: Optional[date] = Field(default=None, description="Date to scrape norms for (defaults to yesterday)")
    force: bool = Field(default=False, description="Force fresh scraping, bypass cache")

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_date": "2025-10-15",
                "force": False
            }
        }
    }


class DateRangeScrapeRequest(BaseModel):
    """Request model for date range scraping"""
    start_date: date = Field(description="Start date (inclusive)")
    end_date: date = Field(description="End date (inclusive)")
    force: bool = Field(default=False, description="Force fresh scraping, bypass cache")

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_date": "2025-10-01",
                "end_date": "2025-10-15",
                "force": False
            }
        }
    }