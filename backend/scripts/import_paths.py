#!/usr/bin/env python3
"""
Import paths from GeoJSON file into the database.

Usage:
    python scripts/import_paths.py --file /data/Calderdale-JSON.json --area "CMBC RoW Network"
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from shapely.geometry import shape
from geoalchemy2.shape import from_shape

from app.config import DATABASE_URL
from app.db import Base
from app.models import Path


def calculate_length_km(geometry):
    """Calculate approximate length in km using Haversine-based approach."""
    if geometry is None:
        return 0.0

    coords = list(geometry.coords)
    if len(coords) < 2:
        return 0.0

    from math import radians, sin, cos, sqrt, atan2

    total_length = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i][:2]
        lon2, lat2 = coords[i + 1][:2]

        R = 6371  # Earth's radius in km

        lat1, lat2 = radians(lat1), radians(lat2)
        lon1, lon2 = radians(lon1), radians(lon2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        total_length += R * c

    return total_length


def import_paths(filepath: str, area: str, clear_existing: bool = False):
    """Import paths from GeoJSON file."""

    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)

    # Ensure PostGIS extension exists
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

    # Create tables
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    if clear_existing:
        print(f"Clearing existing paths for area: {area}")
        session.query(Path).filter(Path.area == area).delete()
        session.commit()

    print(f"Loading GeoJSON from: {filepath}")
    with open(filepath, 'r') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f"Found {len(features)} features to import")

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

            # Map StatusDesc to path_type
            path_type = props.get('StatusDesc', 'Unknown')

            # Skip footpaths - they are not displayed or tracked
            if path_type == 'Footpath':
                skipped += 1
                continue

            path = Path(
                source_fid=str(props.get('fid', '')),
                route_code=props.get('RouteCode', ''),
                name=props.get('Name', ''),
                path_type=path_type,
                area=area,
                geometry=from_shape(geom, srid=4326),
                length_km=calculate_length_km(geom)
            )

            session.add(path)
            imported += 1

            if (i + 1) % 500 == 0:
                session.commit()
                print(f"  Processed {i + 1}/{len(features)}...")

        except Exception as e:
            print(f"  Error importing feature {i}: {e}")
            skipped += 1
            continue

    session.commit()
    session.close()

    print(f"\nImport complete!")
    print(f"  Imported: {imported}")
    print(f"  Skipped: {skipped}")


def main():
    parser = argparse.ArgumentParser(description='Import paths from GeoJSON')
    parser.add_argument('--file', required=True, help='Path to GeoJSON file')
    parser.add_argument('--area', required=True, help='Area name for imported paths')
    parser.add_argument('--clear', action='store_true', help='Clear existing paths for this area first')

    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    import_paths(args.file, args.area, args.clear)


if __name__ == '__main__':
    main()
