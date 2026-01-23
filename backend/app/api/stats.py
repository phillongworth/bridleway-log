from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.db import get_db
from app.models import Path

router = APIRouter()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    Get aggregated statistics including coverage data.
    """
    # Base filter: exclude footpaths
    base_filter = Path.path_type != "Footpath"

    # Total counts (excluding footpaths)
    total_paths = db.query(func.count(Path.id)).filter(base_filter).scalar() or 0
    total_length = db.query(func.sum(Path.length_km)).filter(base_filter).scalar() or 0

    # Coverage counts (excluding footpaths)
    ridden_paths = db.query(func.count(Path.id)).filter(base_filter, Path.is_ridden == True).scalar() or 0
    not_ridden_paths = total_paths - ridden_paths

    ridden_length = db.query(func.sum(Path.length_km)).filter(base_filter, Path.is_ridden == True).scalar() or 0
    not_ridden_length = total_length - ridden_length

    # Stats by path type (including coverage, excluding footpaths)
    by_type_query = db.query(
        Path.path_type,
        func.count(Path.id).label('count'),
        func.sum(Path.length_km).label('length'),
        func.count(Path.id).filter(Path.is_ridden == True).label('ridden_count'),
        func.sum(Path.length_km).filter(Path.is_ridden == True).label('ridden_length')
    ).filter(base_filter).group_by(Path.path_type).all()

    by_type = {}
    for path_type, count, length, ridden_count, ridden_len in by_type_query:
        by_type[path_type or "Unknown"] = {
            "count": count,
            "length_km": round(length or 0, 3),
            "ridden_count": ridden_count or 0,
            "ridden_length_km": round(ridden_len or 0, 3),
            "not_ridden_count": count - (ridden_count or 0),
            "not_ridden_length_km": round((length or 0) - (ridden_len or 0), 3)
        }

    # Stats by area (including coverage, excluding footpaths)
    by_area_query = db.query(
        Path.area,
        func.count(Path.id).label('count'),
        func.sum(Path.length_km).label('length'),
        func.count(Path.id).filter(Path.is_ridden == True).label('ridden_count'),
        func.sum(Path.length_km).filter(Path.is_ridden == True).label('ridden_length')
    ).filter(base_filter).group_by(Path.area).all()

    by_area = {}
    for area, count, length, ridden_count, ridden_len in by_area_query:
        by_area[area or "Unknown"] = {
            "count": count,
            "length_km": round(length or 0, 3),
            "ridden_count": ridden_count or 0,
            "ridden_length_km": round(ridden_len or 0, 3),
            "not_ridden_count": count - (ridden_count or 0),
            "not_ridden_length_km": round((length or 0) - (ridden_len or 0), 3)
        }

    return {
        "total_paths": total_paths,
        "total_length_km": round(total_length, 3),
        "ridden_paths": ridden_paths,
        "not_ridden_paths": not_ridden_paths,
        "ridden_length_km": round(ridden_length, 3),
        "not_ridden_length_km": round(not_ridden_length, 3),
        "by_type": by_type,
        "by_area": by_area
    }


@router.get("/areas")
def get_areas(db: Session = Depends(get_db)):
    areas = db.query(Path.area).distinct().order_by(Path.area).all()
    return {"areas": [a[0] for a in areas if a[0]]}
