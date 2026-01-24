"""
Bridleways API endpoints for GeoJSON upload and import.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from shapely.geometry import shape
from geoalchemy2.shape import from_shape
from typing import Optional
import json
import os
import logging
from math import radians, sin, cos, sqrt, atan2

from app.db import get_db
from app.models import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# Data directory for storing uploaded GeoJSON files
DATA_DIR = "/data"


def calculate_length_km(geometry) -> float:
    """Calculate approximate length in km using Haversine-based approach."""
    if geometry is None:
        return 0.0

    coords = list(geometry.coords)
    if len(coords) < 2:
        return 0.0

    total_length = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i][:2]
        lon2, lat2 = coords[i + 1][:2]

        R = 6371  # Earth's radius in km

        lat1_r, lat2_r = radians(lat1), radians(lat2)
        lon1_r, lon2_r = radians(lon1), radians(lon2)

        dlat = lat2_r - lat1_r
        dlon = lon2_r - lon1_r

        a = sin(dlat/2)**2 + cos(lat1_r) * cos(lat2_r) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        total_length += R * c

    return total_length


@router.post("/bridleways/upload")
async def upload_bridleways(
    file: UploadFile = File(...),
    area: str = Form(...),
    clear_existing: bool = Form(False),
    db: Session = Depends(get_db)
):
    """
    Upload a GeoJSON file containing bridleway data for an area.

    - file: GeoJSON file containing path features
    - area: Name of the area (e.g., "Bradford", "Wakefield")
    - clear_existing: If true, removes existing paths for this area before import

    All paths are imported as type "Bridleway" regardless of source data.
    The uploaded file is saved to the data directory.
    """
    if not file.filename or not file.filename.endswith('.json') and not file.filename.endswith('.geojson'):
        raise HTTPException(status_code=400, detail="File must be a .json or .geojson file")

    try:
        # Read file content
        content = await file.read()
        data = json.loads(content.decode('utf-8'))

        features = data.get('features', [])
        if not features:
            raise HTTPException(status_code=400, detail="No features found in GeoJSON file")

        # Save file to data directory
        safe_filename = "".join(c for c in file.filename if c.isalnum() or c in '._-').strip()
        if not safe_filename:
            safe_filename = f"{area.replace(' ', '_')}.json"

        filepath = os.path.join(DATA_DIR, safe_filename)
        with open(filepath, 'wb') as f:
            f.write(content)

        # Clear existing paths for this area if requested
        if clear_existing:
            deleted = db.query(Path).filter(Path.area == area).delete()
            db.commit()
            logger.info(f"Cleared {deleted} existing paths for area: {area}")

        # Import paths
        imported = 0
        skipped = 0

        for i, feature in enumerate(features):
            try:
                props = feature.get('properties', {})
                geom_data = feature.get('geometry')

                if geom_data is None:
                    skipped += 1
                    continue

                geom = shape(geom_data)

                # Force all paths to be Bridleway type
                path_type = "Bridleway"

                # Extract name from various possible property names
                name = (props.get('Name') or props.get('name') or
                       props.get('NAME') or props.get('RouteCode') or
                       props.get('route_code') or '')

                path = Path(
                    source_fid=str(props.get('fid', props.get('FID', props.get('id', '')))),
                    route_code=props.get('RouteCode', props.get('route_code', '')),
                    name=name,
                    path_type=path_type,
                    area=area,
                    geometry=from_shape(geom, srid=4326),
                    length_km=calculate_length_km(geom)
                )

                db.add(path)
                imported += 1

                # Commit in batches
                if (i + 1) % 500 == 0:
                    db.commit()

            except Exception as e:
                logger.error(f"Error importing feature {i}: {e}")
                skipped += 1
                continue

        db.commit()

        return {
            "status": "success",
            "message": f"Imported {imported} bridleways for area '{area}'",
            "area": area,
            "imported": imported,
            "skipped": skipped,
            "file_saved": filepath
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error uploading bridleways: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bridleways/area/{area_name}")
def delete_area(area_name: str, db: Session = Depends(get_db)):
    """
    Delete all bridleways for a specific area.
    """
    deleted = db.query(Path).filter(Path.area == area_name).delete()
    db.commit()

    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"No paths found for area: {area_name}")

    return {
        "status": "success",
        "message": f"Deleted {deleted} paths for area '{area_name}'",
        "area": area_name,
        "deleted": deleted
    }
