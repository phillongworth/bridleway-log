from pydantic import BaseModel
from typing import Optional


class PathProperties(BaseModel):
    id: int
    source_fid: Optional[str]
    route_code: Optional[str]
    name: Optional[str]
    path_type: Optional[str]
    area: Optional[str]
    length_km: Optional[float]


class StatsResponse(BaseModel):
    total_paths: int
    total_length_km: float
    by_type: dict[str, dict]
    by_area: dict[str, dict]


class AreaResponse(BaseModel):
    areas: list[str]
