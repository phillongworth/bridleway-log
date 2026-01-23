from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PathProperties(BaseModel):
    id: int
    source_fid: Optional[str]
    route_code: Optional[str]
    name: Optional[str]
    path_type: Optional[str]
    area: Optional[str]
    length_km: Optional[float]
    # Coverage fields (iteration 2)
    is_ridden: bool = False
    coverage_fraction: float = 0.0
    last_ridden_date: Optional[datetime] = None


class StatsResponse(BaseModel):
    total_paths: int
    total_length_km: float
    ridden_paths: int
    not_ridden_paths: int
    ridden_length_km: float
    not_ridden_length_km: float
    by_type: dict[str, dict]
    by_area: dict[str, dict]


class AreaResponse(BaseModel):
    areas: list[str]


# Ride schemas
class RideBase(BaseModel):
    filename: str
    date_recorded: Optional[datetime] = None
    distance_km: float = 0.0
    elevation_gain_m: Optional[float] = None


class RideResponse(RideBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RideListResponse(BaseModel):
    rides: list[RideResponse]
    total: int


class RideUploadResult(BaseModel):
    filename: str
    status: str  # "imported", "skipped_duplicate", "error"
    message: str
    ride_id: Optional[int] = None


class RideUploadResponse(BaseModel):
    total_files: int
    imported: int
    skipped: int
    errors: int
    results: list[RideUploadResult]


class CoverageRecomputeResponse(BaseModel):
    paths_updated: int
    message: str
