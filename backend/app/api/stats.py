from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import Path

router = APIRouter()


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_paths = db.query(func.count(Path.id)).scalar()
    total_length = db.query(func.sum(Path.length_km)).scalar() or 0

    # Stats by path type
    by_type_query = db.query(
        Path.path_type,
        func.count(Path.id),
        func.sum(Path.length_km)
    ).group_by(Path.path_type).all()

    by_type = {}
    for path_type, count, length in by_type_query:
        by_type[path_type or "Unknown"] = {
            "count": count,
            "length_km": round(length or 0, 3)
        }

    # Stats by area
    by_area_query = db.query(
        Path.area,
        func.count(Path.id),
        func.sum(Path.length_km)
    ).group_by(Path.area).all()

    by_area = {}
    for area, count, length in by_area_query:
        by_area[area or "Unknown"] = {
            "count": count,
            "length_km": round(length or 0, 3)
        }

    return {
        "total_paths": total_paths,
        "total_length_km": round(total_length, 3),
        "by_type": by_type,
        "by_area": by_area
    }


@router.get("/areas")
def get_areas(db: Session = Depends(get_db)):
    areas = db.query(Path.area).distinct().order_by(Path.area).all()
    return {"areas": [a[0] for a in areas if a[0]]}
