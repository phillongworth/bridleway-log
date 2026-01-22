from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2.functions import ST_AsGeoJSON
from typing import Optional
import json

from app.db import get_db
from app.models import Path

router = APIRouter()


@router.get("/paths")
def get_paths(
    area: Optional[list[str]] = Query(None),
    path_type: Optional[list[str]] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(
        Path.id,
        Path.source_fid,
        Path.route_code,
        Path.name,
        Path.path_type,
        Path.area,
        Path.length_km,
        func.ST_AsGeoJSON(Path.geometry).label("geometry")
    )

    if area:
        query = query.filter(Path.area.in_(area))
    if path_type:
        query = query.filter(Path.path_type.in_(path_type))

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
                "length_km": round(p.length_km, 3) if p.length_km else None
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
    types = db.query(Path.path_type).distinct().order_by(Path.path_type).all()
    return {"path_types": [t[0] for t in types if t[0]]}
