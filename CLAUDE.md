# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bridleway Log is a web application for viewing public rights of way (footpaths, bridleways, etc.) on an interactive map. It uses FastAPI + PostGIS backend with a vanilla JavaScript + Leaflet frontend.

**Version 2.0** adds GPX upload and real ridden coverage tracking.

## Common Commands

```bash
# Start the application
docker compose up -d

# Stop the application
docker compose down

# Rebuild after code changes
docker compose build web && docker compose up -d

# View logs
docker compose logs -f web

# Run database migration (required for v2.0 upgrade)
docker compose run --rm web python scripts/migrate.py

# Import path data from GeoJSON
docker compose run --rm web python scripts/import_paths.py \
    --file /data/Calderdale-JSON.json \
    --area "CMBC RoW Network"

# Import with --clear to replace existing data for an area
docker compose run --rm web python scripts/import_paths.py \
    --file /data/filename.json --area "Area Name" --clear

# Access PostgreSQL directly
docker compose exec db psql -U bridleway -d bridleway_log
```

## Architecture

**Backend (FastAPI):**
- `backend/app/main.py` - Application entry point, mounts static files and API routers
- `backend/app/models.py` - SQLAlchemy models for `Path` and `Ride` with PostGIS geometry
- `backend/app/api/paths.py` - `/api/paths` endpoint returning GeoJSON FeatureCollection
- `backend/app/api/stats.py` - `/api/stats` and `/api/areas` endpoints
- `backend/app/api/rides.py` - `/api/rides` endpoints for GPX upload and management
- `backend/app/services/coverage.py` - Coverage calculation using PostGIS spatial operations
- `backend/scripts/import_paths.py` - CLI script to import GeoJSON data
- `backend/scripts/migrate.py` - Database migration script

**Frontend (served from `/app/static/` in container):**
- `frontend/index.html` - Single page with sidebar filters, upload UI, and Leaflet map
- `frontend/assets/js/main.js` - All frontend logic (map init, API calls, filtering, GPX upload)
- `frontend/assets/css/styles.css` - Styling including coverage colors

**Data flow:** GeoJSON file → import script → PostGIS database → FastAPI endpoints → Leaflet map

## API Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/paths?area=&path_type=&ridden=&min_coverage=` | GeoJSON FeatureCollection with coverage data |
| `GET /api/stats` | Path counts, lengths, and coverage statistics |
| `GET /api/areas` | List of distinct area names |
| `GET /api/path-types` | List of path types |
| `POST /api/rides/upload` | Upload GPX files (multipart form) |
| `GET /api/rides` | List of uploaded rides |
| `DELETE /api/rides/{id}` | Delete a ride and recompute coverage |
| `POST /api/coverage/recompute` | Manually trigger coverage recalculation |

## GPX Upload & Coverage

### How to Upload GPX
1. Use the "Upload GPX" section in the sidebar
2. Select one or more .gpx files
3. Click Upload
4. Coverage is automatically recalculated after upload

### Coverage Calculation
A path is marked as "ridden" based on spatial overlap with GPX track geometries:

- **Rule**: A path is ridden if at least **80%** of its length is within **30 meters** of any GPX track
- **Parameters** (in `backend/app/services/coverage.py`):
  - `COVERAGE_MIN_FRACTION = 0.8` (80%)
  - `COVERAGE_BUFFER_METERS = 30` (30m buffer)

The calculation uses PostGIS spatial operations:
1. All ride geometries are buffered by 30m and unioned
2. Each path is intersected with this buffered area
3. Coverage fraction = (intersection length) / (path length)
4. `is_ridden` = coverage_fraction >= 0.8

### Known Limitations
- Coverage is approximate due to GPS accuracy variations
- Large datasets may have slower recalculation times
- The 30m buffer may not perfectly match all riding scenarios

## GeoJSON Import Format

The import script expects features with these properties:
- `fid` → `source_fid`
- `RouteCode` → `route_code`
- `Name` → `name`
- `StatusDesc` → `path_type` (Footpath, Bridleway, Restricted Byway, BOAT)

## Environment

- Runs on port 6080 (maps to container port 8000)
- PostgreSQL with PostGIS extension
- Data files mounted at `/data/` inside containers
- Frontend served by FastAPI (no separate web server needed)

## Database Models

**Path** (paths table):
- `id`, `source_fid`, `route_code`, `name`, `path_type`, `area`
- `geometry` (LINESTRING, SRID 4326)
- `length_km`
- `is_ridden` (boolean)
- `coverage_fraction` (float 0-1)
- `last_ridden_date` (timestamp)

**Ride** (rides table):
- `id`, `filename`, `file_hash` (SHA-256 for deduplication)
- `date_recorded`, `distance_km`, `elevation_gain_m`
- `geometry` (MULTILINESTRING, SRID 4326)
- `created_at`
