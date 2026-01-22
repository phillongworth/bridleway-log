# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bridleway Log is a web application for viewing public rights of way (footpaths, bridleways, etc.) on an interactive map. It uses FastAPI + PostGIS backend with a vanilla JavaScript + Leaflet frontend.

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
- `backend/app/models.py` - SQLAlchemy model for `Path` with PostGIS geometry
- `backend/app/api/paths.py` - `/api/paths` endpoint returning GeoJSON FeatureCollection
- `backend/app/api/stats.py` - `/api/stats` and `/api/areas` endpoints
- `backend/scripts/import_paths.py` - CLI script to import GeoJSON data

**Frontend (served from `/app/static/` in container):**
- `frontend/index.html` - Single page with sidebar filters and Leaflet map
- `frontend/assets/js/main.js` - All frontend logic (map init, API calls, filtering)
- `frontend/assets/css/styles.css` - Styling including path type colors

**Data flow:** GeoJSON file → import script → PostGIS database → FastAPI endpoints → Leaflet map

## API Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/paths?area=&path_type=` | GeoJSON FeatureCollection |
| `GET /api/stats` | Path counts and lengths by type/area |
| `GET /api/areas` | List of distinct area names |
| `GET /api/path-types` | List of path types |

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
