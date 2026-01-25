"""
Coverage calculation service using PostGIS spatial operations.

Coverage rule:
- A path is considered "ridden" if at least COVERAGE_MIN_FRACTION of its length
  is within COVERAGE_BUFFER_METERS of any GPX track geometry.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Coverage parameters (can be made configurable via environment later)
COVERAGE_MIN_FRACTION = 0.5  # 50% of path must be covered
COVERAGE_BUFFER_METERS = 30  # 30 meter buffer around GPX tracks

# Use British National Grid (EPSG:27700) for accurate UK distance calculations
# Web Mercator (3857) has significant distortion at UK latitudes
UK_SRID = 27700


def recompute_coverage(db: Session, path_ids: Optional[list[int]] = None) -> int:
    """
    Recompute coverage for paths based on spatial overlap with ride geometries.

    Args:
        db: Database session
        path_ids: Optional list of path IDs to update. If None, updates all paths.

    Returns:
        Number of paths updated.
    """

    # First, check if there are any rides
    ride_count = db.execute(text("SELECT COUNT(*) FROM rides")).scalar()

    if ride_count == 0:
        # No rides, reset all paths to not ridden
        if path_ids:
            result = db.execute(
                text("""
                    UPDATE paths
                    SET is_ridden = FALSE,
                        coverage_fraction = 0.0,
                        last_ridden_date = NULL
                    WHERE id = ANY(:path_ids)
                """),
                {"path_ids": path_ids}
            )
        else:
            result = db.execute(
                text("""
                    UPDATE paths
                    SET is_ridden = FALSE,
                        coverage_fraction = 0.0,
                        last_ridden_date = NULL
                """)
            )
        db.commit()
        return result.rowcount

    # Build the coverage calculation query
    # Uses ST_Transform to convert to a meter-based CRS (EPSG:3857) for buffering
    # Then calculates intersection length as fraction of total path length

    path_filter = ""
    params = {
        "buffer_meters": COVERAGE_BUFFER_METERS,
        "min_fraction": COVERAGE_MIN_FRACTION
    }

    if path_ids:
        path_filter = "WHERE p.id = ANY(:path_ids)"
        params["path_ids"] = path_ids

    coverage_query = text(f"""
        WITH ride_buffer AS (
            -- Create a single buffered geometry from all rides
            -- Transform to British National Grid (EPSG:27700) for accurate UK measurements
            SELECT ST_Union(
                ST_Buffer(
                    ST_Transform(geometry, {UK_SRID}),
                    :buffer_meters
                )
            ) AS buffered_geom
            FROM rides
            WHERE geometry IS NOT NULL
        ),
        path_coverage AS (
            SELECT
                p.id,
                -- Calculate length of path that intersects with ride buffer
                CASE
                    WHEN rb.buffered_geom IS NOT NULL AND ST_Intersects(
                        ST_Transform(p.geometry, {UK_SRID}),
                        rb.buffered_geom
                    ) THEN
                        ST_Length(
                            ST_Intersection(
                                ST_Transform(p.geometry, {UK_SRID}),
                                rb.buffered_geom
                            )
                        ) / NULLIF(ST_Length(ST_Transform(p.geometry, {UK_SRID})), 0)
                    ELSE 0.0
                END AS coverage_frac,
                -- Get the most recent ride date that intersects this path
                (
                    SELECT MAX(r.date_recorded)
                    FROM rides r
                    WHERE r.geometry IS NOT NULL
                      AND r.date_recorded IS NOT NULL
                      AND ST_DWithin(
                          ST_Transform(p.geometry, {UK_SRID}),
                          ST_Transform(r.geometry, {UK_SRID}),
                          :buffer_meters
                      )
                ) AS last_ride_date
            FROM paths p
            CROSS JOIN ride_buffer rb
            {path_filter}
        )
        UPDATE paths
        SET
            coverage_fraction = COALESCE(pc.coverage_frac, 0.0),
            is_ridden = (COALESCE(pc.coverage_frac, 0.0) >= :min_fraction),
            last_ridden_date = pc.last_ride_date
        FROM path_coverage pc
        WHERE paths.id = pc.id
    """)

    result = db.execute(coverage_query, params)
    db.commit()

    updated_count = result.rowcount
    logger.info(f"Updated coverage for {updated_count} paths")

    return updated_count


def get_coverage_stats(db: Session) -> dict:
    """
    Get summary statistics about path coverage.

    Returns:
        Dictionary with coverage statistics.
    """
    result = db.execute(text("""
        SELECT
            COUNT(*) AS total_paths,
            COUNT(*) FILTER (WHERE is_ridden = TRUE) AS ridden_paths,
            COUNT(*) FILTER (WHERE is_ridden = FALSE OR is_ridden IS NULL) AS not_ridden_paths,
            COALESCE(SUM(length_km), 0) AS total_length_km,
            COALESCE(SUM(length_km) FILTER (WHERE is_ridden = TRUE), 0) AS ridden_length_km,
            COALESCE(SUM(length_km) FILTER (WHERE is_ridden = FALSE OR is_ridden IS NULL), 0) AS not_ridden_length_km,
            AVG(coverage_fraction) AS avg_coverage
        FROM paths
    """)).fetchone()

    return {
        "total_paths": result[0] or 0,
        "ridden_paths": result[1] or 0,
        "not_ridden_paths": result[2] or 0,
        "total_length_km": round(result[3] or 0, 3),
        "ridden_length_km": round(result[4] or 0, 3),
        "not_ridden_length_km": round(result[5] or 0, 3),
        "average_coverage": round(result[6] or 0, 3)
    }
