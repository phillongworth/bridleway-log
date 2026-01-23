from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_AsGeoJSON
from typing import Optional
import json

from app.db import get_db
from app.models import Path

router = APIRouter()


@router.get("/paths/excluded")
def get_excluded_paths(
    db: Session = Depends(get_db)
):
    """
    Get excluded paths (footpaths) as GeoJSON FeatureCollection.
    Used for reviewing what has been filtered out.
    """
    query = db.query(
        Path.id,
        Path.source_fid,
        Path.route_code,
        Path.name,
        Path.path_type,
        Path.area,
        Path.length_km,
        Path.is_ridden,
        Path.coverage_fraction,
        Path.last_ridden_date,
        func.ST_AsGeoJSON(Path.geometry).label("geometry")
    )

    # Only return footpaths (excluded from main view)
    query = query.filter(Path.path_type == "Footpath")

    paths = query.all()

    features = []
    for p in paths:
        feature = {
            "type": "Feature",
            "properties": {
                "id": p.id,
                "source_fid": p.source_fid,
                "route_code": p.route_code,
                "name": p.name,
                "path_type": p.path_type,
                "area": p.area,
                "length_km": round(p.length_km, 3) if p.length_km else None,
                "is_ridden": p.is_ridden or False,
                "coverage_fraction": round(p.coverage_fraction, 3) if p.coverage_fraction else 0.0,
                "last_ridden_date": p.last_ridden_date.isoformat() if p.last_ridden_date else None
            },
            "geometry": json.loads(p.geometry) if p.geometry else None
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get("/paths")
def get_paths(
    area: Optional[list[str]] = Query(None),
    path_type: Optional[list[str]] = Query(None),
    ridden: Optional[bool] = Query(None, description="Filter by ridden status"),
    min_coverage: Optional[float] = Query(None, ge=0, le=1, description="Minimum coverage fraction (0-1)"),
    db: Session = Depends(get_db)
):
    """
    Get paths as GeoJSON FeatureCollection.

    Query parameters:
    - area: Filter by area name(s) - can be specified multiple times
    - path_type: Filter by path type(s) - can be specified multiple times
    - ridden: Filter by ridden status (true/false)
    - min_coverage: Filter paths with coverage >= this value (0-1)
    """
    query = db.query(
        Path.id,
        Path.source_fid,
        Path.route_code,
        Path.name,
        Path.path_type,
        Path.area,
        Path.length_km,
        Path.is_ridden,
        Path.coverage_fraction,
        Path.last_ridden_date,
        func.ST_AsGeoJSON(Path.geometry).label("geometry")
    )

    # Always exclude footpaths
    query = query.filter(Path.path_type != "Footpath")

    if area:
        query = query.filter(Path.area.in_(area))
    if path_type:
        query = query.filter(Path.path_type.in_(path_type))
    if ridden is not None:
        query = query.filter(Path.is_ridden == ridden)
    if min_coverage is not None:
        query = query.filter(Path.coverage_fraction >= min_coverage)

    paths = query.all()

    features = []
    for p in paths:
        feature = {
            "type": "Feature",
            "properties": {
                "id": p.id,
                "source_fid": p.source_fid,
                "route_code": p.route_code,
                "name": p.name,
                "path_type": p.path_type,
                "area": p.area,
                "length_km": round(p.length_km, 3) if p.length_km else None,
                "is_ridden": p.is_ridden or False,
                "coverage_fraction": round(p.coverage_fraction, 3) if p.coverage_fraction else 0.0,
                "last_ridden_date": p.last_ridden_date.isoformat() if p.last_ridden_date else None
            },
            "geometry": json.loads(p.geometry) if p.geometry else None
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get("/path-types")
def get_path_types(db: Session = Depends(get_db)):
    types = db.query(Path.path_type).filter(Path.path_type != "Footpath").distinct().order_by(Path.path_type).all()
    return {"path_types": [t[0] for t in types if t[0]]}
