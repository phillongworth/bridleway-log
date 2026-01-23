"""
Rides API endpoints for GPX upload and management.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2 import WKTElement
from typing import Optional
import hashlib
import json
import gpxpy
import gpxpy.gpx
import logging

from app.db import get_db
from app.models import Ride
from app.schemas import (
    RideResponse,
    RideListResponse,
    RideUploadResult,
    RideUploadResponse,
    CoverageRecomputeResponse
)
from app.services.coverage import recompute_coverage

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_gpx_file(content: bytes) -> tuple[Optional[str], Optional[str], float, Optional[float]]:
    """
    Parse GPX file content and extract geometry and metadata.

    Returns:
        Tuple of (wkt_geometry, date_recorded, distance_km, elevation_gain_m)
    """
    gpx = gpxpy.parse(content.decode('utf-8'))

    all_coords = []
    total_distance = 0.0
    elevation_gain = 0.0
    min_time = None
    prev_elevation = None

    # Process all tracks
    for track in gpx.tracks:
        for segment in track.segments:
            segment_coords = []
            for i, point in enumerate(segment.points):
                segment_coords.append((point.longitude, point.latitude))

                # Track time for date_recorded
                if point.time:
                    if min_time is None or point.time < min_time:
                        min_time = point.time

                # Calculate elevation gain
                if point.elevation is not None:
                    if prev_elevation is not None:
                        elev_diff = point.elevation - prev_elevation
                        if elev_diff > 0:
                            elevation_gain += elev_diff
                    prev_elevation = point.elevation

            if len(segment_coords) >= 2:
                all_coords.append(segment_coords)

            # Calculate distance using gpxpy's built-in method
            total_distance += segment.length_3d() if segment.has_elevations() else segment.length_2d()

    # Also process waypoints if there are routes but no tracks
    if not all_coords:
        for route in gpx.routes:
            route_coords = []
            for point in route.points:
                route_coords.append((point.longitude, point.latitude))
                if point.time:
                    if min_time is None or point.time < min_time:
                        min_time = point.time
            if len(route_coords) >= 2:
                all_coords.append(route_coords)

    if not all_coords:
        return None, None, 0.0, None

    # Convert to WKT MultiLineString
    if len(all_coords) == 1:
        # Single linestring
        coords_str = ", ".join(f"{lon} {lat}" for lon, lat in all_coords[0])
        wkt = f"MULTILINESTRING(({coords_str}))"
    else:
        # Multiple linestrings
        linestrings = []
        for coords in all_coords:
            coords_str = ", ".join(f"{lon} {lat}" for lon, lat in coords)
            linestrings.append(f"({coords_str})")
        wkt = f"MULTILINESTRING({', '.join(linestrings)})"

    date_recorded = min_time.isoformat() if min_time else None
    distance_km = total_distance / 1000.0  # Convert meters to km

    return wkt, date_recorded, distance_km, elevation_gain if elevation_gain > 0 else None


@router.post("/rides/upload", response_model=RideUploadResponse)
async def upload_rides(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload one or more GPX files.

    Each GPX file is parsed and stored as a Ride record.
    After upload, coverage is recomputed for all paths.
    """
    results = []
    imported = 0
    skipped = 0
    errors = 0

    for file in files:
        try:
            # Read file content
            content = await file.read()

            # Calculate file hash for deduplication
            file_hash = hashlib.sha256(content).hexdigest()

            # Check for duplicate
            existing = db.query(Ride).filter(Ride.file_hash == file_hash).first()
            if existing:
                results.append(RideUploadResult(
                    filename=file.filename or "unknown",
                    status="skipped_duplicate",
                    message=f"Duplicate file (matches ride ID {existing.id})"
                ))
                skipped += 1
                continue

            # Parse GPX content
            wkt, date_recorded, distance_km, elevation_gain = parse_gpx_file(content)

            if not wkt:
                results.append(RideUploadResult(
                    filename=file.filename or "unknown",
                    status="error",
                    message="No valid track or route data found in GPX file"
                ))
                errors += 1
                continue

            # Create Ride record
            ride = Ride(
                filename=file.filename or "unknown.gpx",
                file_hash=file_hash,
                date_recorded=date_recorded,
                distance_km=round(distance_km, 3),
                elevation_gain_m=round(elevation_gain, 1) if elevation_gain else None,
                geometry=WKTElement(wkt, srid=4326)
            )

            db.add(ride)
            db.commit()
            db.refresh(ride)

            results.append(RideUploadResult(
                filename=file.filename or "unknown",
                status="imported",
                message=f"Imported successfully ({distance_km:.2f} km)",
                ride_id=ride.id
            ))
            imported += 1

        except Exception as e:
            logger.error(f"Error processing GPX file {file.filename}: {e}")
            results.append(RideUploadResult(
                filename=file.filename or "unknown",
                status="error",
                message=str(e)
            ))
            errors += 1
            db.rollback()

    # Recompute coverage if any rides were imported
    if imported > 0:
        try:
            recompute_coverage(db)
        except Exception as e:
            logger.error(f"Error recomputing coverage: {e}")

    return RideUploadResponse(
        total_files=len(files),
        imported=imported,
        skipped=skipped,
        errors=errors,
        results=results
    )


@router.get("/rides", response_model=RideListResponse)
def get_rides(db: Session = Depends(get_db)):
    """
    Get list of all rides.
    """
    rides = db.query(
        Ride.id,
        Ride.filename,
        Ride.date_recorded,
        Ride.distance_km,
        Ride.elevation_gain_m,
        Ride.created_at
    ).order_by(Ride.date_recorded.desc().nulls_last()).all()

    ride_list = [
        RideResponse(
            id=r.id,
            filename=r.filename,
            date_recorded=r.date_recorded,
            distance_km=r.distance_km,
            elevation_gain_m=r.elevation_gain_m,
            created_at=r.created_at
        )
        for r in rides
    ]

    return RideListResponse(rides=ride_list, total=len(ride_list))


@router.get("/rides/geojson")
def get_rides_geojson(db: Session = Depends(get_db)):
    """
    Get all rides as a GeoJSON FeatureCollection.
    """
    rides = db.query(
        Ride.id,
        Ride.filename,
        Ride.date_recorded,
        Ride.distance_km,
        Ride.elevation_gain_m,
        func.ST_AsGeoJSON(Ride.geometry).label('geojson')
    ).filter(Ride.geometry.isnot(None)).all()

    features = []
    for r in rides:
        if r.geojson:
            features.append({
                "type": "Feature",
                "properties": {
                    "id": r.id,
                    "filename": r.filename,
                    "date_recorded": r.date_recorded.isoformat() if r.date_recorded else None,
                    "distance_km": r.distance_km,
                    "elevation_gain_m": r.elevation_gain_m
                },
                "geometry": json.loads(r.geojson)
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.delete("/rides/{ride_id}")
def delete_ride(ride_id: int, db: Session = Depends(get_db)):
    """
    Delete a ride and recompute coverage.
    """
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    db.delete(ride)
    db.commit()

    # Recompute coverage
    try:
        recompute_coverage(db)
    except Exception as e:
        logger.error(f"Error recomputing coverage after delete: {e}")

    return {"message": f"Ride {ride_id} deleted", "id": ride_id}


@router.post("/coverage/recompute", response_model=CoverageRecomputeResponse)
def recompute_coverage_endpoint(db: Session = Depends(get_db)):
    """
    Manually trigger coverage recomputation for all paths.
    """
    try:
        paths_updated = recompute_coverage(db)
        return CoverageRecomputeResponse(
            paths_updated=paths_updated,
            message="Coverage recomputed successfully"
        )
    except Exception as e:
        logger.error(f"Error in coverage recomputation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
