#!/usr/bin/env python3
"""
Batch import GPX files into the database.

Usage:
    python scripts/import_gpx.py --dir /data/gpxfiles/activities
"""

import argparse
import hashlib
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gpxpy
import gpxpy.gpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

from app.config import DATABASE_URL
from app.db import Base
from app.models import Ride
from app.services.coverage import recompute_coverage


def parse_gpx_file(content: bytes) -> tuple:
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
            for point in segment.points:
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

            # Calculate distance
            total_distance += segment.length_3d() if segment.has_elevations() else segment.length_2d()

    # Also process routes if no tracks
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
        coords_str = ", ".join(f"{lon} {lat}" for lon, lat in all_coords[0])
        wkt = f"MULTILINESTRING(({coords_str}))"
    else:
        linestrings = []
        for coords in all_coords:
            coords_str = ", ".join(f"{lon} {lat}" for lon, lat in coords)
            linestrings.append(f"({coords_str})")
        wkt = f"MULTILINESTRING({', '.join(linestrings)})"

    date_recorded = min_time.isoformat() if min_time else None
    distance_km = total_distance / 1000.0

    return wkt, date_recorded, distance_km, elevation_gain if elevation_gain > 0 else None


def import_gpx_files(directory: str, skip_existing: bool = True):
    """Import all GPX files from a directory."""

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    gpx_dir = Path(directory)
    gpx_files = sorted(gpx_dir.glob("*.gpx"))

    print(f"Found {len(gpx_files)} GPX files to import")

    imported = 0
    skipped = 0
    errors = 0

    for i, gpx_path in enumerate(gpx_files, 1):
        if i % 50 == 0 or i == len(gpx_files):
            print(f"Processing {i}/{len(gpx_files)}... (imported: {imported}, skipped: {skipped}, errors: {errors})")

        try:
            # Read file content
            with open(gpx_path, 'rb') as f:
                content = f.read()

            # Calculate file hash for deduplication
            file_hash = hashlib.sha256(content).hexdigest()

            # Check for duplicate
            if skip_existing:
                existing = session.query(Ride).filter(Ride.file_hash == file_hash).first()
                if existing:
                    skipped += 1
                    continue

            # Parse GPX content
            wkt, date_recorded, distance_km, elevation_gain = parse_gpx_file(content)

            if not wkt:
                print(f"  Warning: No valid track data in {gpx_path.name}")
                errors += 1
                continue

            # Create Ride record
            ride = Ride(
                filename=gpx_path.name,
                file_hash=file_hash,
                date_recorded=date_recorded,
                distance_km=round(distance_km, 3),
                elevation_gain_m=round(elevation_gain, 1) if elevation_gain else None,
                geometry=WKTElement(wkt, srid=4326)
            )

            session.add(ride)
            session.commit()
            imported += 1

        except Exception as e:
            print(f"  Error processing {gpx_path.name}: {e}")
            errors += 1
            session.rollback()

    print(f"\nImport complete: {imported} imported, {skipped} skipped (duplicates), {errors} errors")

    # Recompute coverage
    if imported > 0:
        print("\nRecomputing path coverage...")
        try:
            paths_updated = recompute_coverage(session)
            print(f"Coverage updated for {paths_updated} paths")
        except Exception as e:
            print(f"Error recomputing coverage: {e}")

    session.close()
    return imported, skipped, errors


def main():
    parser = argparse.ArgumentParser(description='Import GPX files into the database')
    parser.add_argument('--dir', required=True, help='Directory containing GPX files')
    parser.add_argument('--no-skip', action='store_true', help='Do not skip existing files (by hash)')

    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Error: Directory not found: {args.dir}")
        sys.exit(1)

    import_gpx_files(args.dir, skip_existing=not args.no_skip)


if __name__ == '__main__':
    main()
