#!/usr/bin/env python3
"""
Database migration script for Bridleway Log.

Applies migrations to add rides table and coverage columns.
Safe to run multiple times (idempotent).

Usage:
    docker compose run --rm web python scripts/migrate.py
"""

import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine, Base
from app.models import Path as PathModel, Ride


def run_migration():
    """Run database migration to add rides table and coverage columns."""

    print("Starting database migration...")

    with engine.connect() as conn:
        # Ensure PostGIS extension is available
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()

        # Check if rides table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'rides'
            )
        """))
        rides_exists = result.scalar()

        if not rides_exists:
            print("Creating rides table...")
            conn.execute(text("""
                CREATE TABLE rides (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    file_hash VARCHAR(64) UNIQUE,
                    date_recorded TIMESTAMP,
                    distance_km FLOAT DEFAULT 0.0,
                    elevation_gain_m FLOAT,
                    geometry GEOMETRY(MULTILINESTRING, 4326),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_rides_file_hash ON rides(file_hash)"))
            conn.execute(text("CREATE INDEX idx_rides_date_recorded ON rides(date_recorded)"))
            conn.execute(text("CREATE INDEX idx_rides_geometry ON rides USING GIST(geometry)"))
            conn.commit()
            print("Rides table created.")
        else:
            print("Rides table already exists.")

        # Check if coverage columns exist in paths
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'paths' AND column_name = 'is_ridden'
            )
        """))
        columns_exist = result.scalar()

        if not columns_exist:
            print("Adding coverage columns to paths table...")
            conn.execute(text("ALTER TABLE paths ADD COLUMN is_ridden BOOLEAN DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE paths ADD COLUMN coverage_fraction FLOAT DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE paths ADD COLUMN last_ridden_date TIMESTAMP"))
            conn.execute(text("CREATE INDEX idx_paths_is_ridden ON paths(is_ridden)"))
            conn.commit()
            print("Coverage columns added.")
        else:
            print("Coverage columns already exist.")

    print("Migration complete!")


if __name__ == "__main__":
    run_migration()
