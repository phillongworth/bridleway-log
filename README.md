# Bridleway Log

A web application for viewing and exploring public rights of way (footpaths, bridleways, etc.) on an interactive map.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, GeoAlchemy2
- **Database:** PostgreSQL with PostGIS
- **Frontend:** HTML, CSS, Vanilla JavaScript, Leaflet
- **Deployment:** Docker Compose

## Quick Start (Linux Server)

Run these commands on your Linux server (e.g., Ubuntu 24.04):

```bash
# Create project directory
sudo mkdir -p /var/www/bridleway-log/data
sudo chown $USER:$USER /var/www/bridleway-log -R

# Navigate to project
cd /var/www/bridleway-log

# Copy your GeoJSON data file to the data directory
# e.g., cp /path/to/Calderdale-JSON.json /var/www/bridleway-log/data/

# Create environment file
cp .env.example .env
# Edit .env and set a secure POSTGRES_PASSWORD

# Start the application
docker compose up -d

# Import path data
docker compose run --rm web python scripts/import_paths.py \
    --file /data/Calderdale-JSON.json \
    --area "CMBC RoW Network"

# Access the application at http://192.168.178.22:6080/
```

## Project Structure

```
/var/www/bridleway-log/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── config.py        # Configuration
│   │   ├── db.py            # Database connection
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── api/
│   │       ├── paths.py     # Path endpoints
│   │       └── stats.py     # Statistics endpoints
│   ├── scripts/
│   │   └── import_paths.py  # Data import script
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   └── assets/
│       ├── js/main.js
│       └── css/styles.css
├── data/
│   └── Calderdale-JSON.json  # Your GeoJSON data
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/paths` | Returns paths as GeoJSON. Query params: `area`, `path_type` |
| `GET /api/stats` | Returns path counts and total lengths |
| `GET /api/areas` | Returns list of distinct area names |
| `GET /api/path-types` | Returns list of path types |

## Importing Additional Data

To import more path data from another GeoJSON file:

```bash
docker compose run --rm web python scripts/import_paths.py \
    --file /data/your-file.json \
    --area "Area Name"
```

Use `--clear` flag to replace existing data for that area:

```bash
docker compose run --rm web python scripts/import_paths.py \
    --file /data/your-file.json \
    --area "Area Name" \
    --clear
```

## GeoJSON Format

The import script expects GeoJSON with these feature properties:
- `fid` - Feature ID
- `RouteCode` - Route code
- `Name` - Path name
- `StatusDesc` - Path type (Footpath, Bridleway, Restricted Byway, BOAT)

## Development (Windows)

To develop locally on Windows before deploying:

1. Install Docker Desktop for Windows
2. Clone the repository
3. Copy `.env.example` to `.env`
4. Run `docker compose up -d`
5. Access at `http://localhost:6080/`

## Stopping the Application

```bash
cd /var/www/bridleway-log
docker compose down
```

To also remove the database volume:

```bash
docker compose down -v
```
