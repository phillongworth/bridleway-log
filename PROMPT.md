You are an expert full‑stack engineer.  
**Target environment:**

* Development machine: Windows (VS Code, Claude Code)  
* **Deployment server: Linux Ubuntu 24.04.3 LTS at `192.168.178.22` on my LAN, Docker already installed**  
* **ALL FILES MUST BE STORED ON THE LINUX MACHINE at `/var/www/bridleway-log/`**  
* Access URL: `http://192.168.178.22:6080`  
* Version control: Git \+ GitHub (project should be suitable for pushing to a public repo and forking)

**CRITICAL: The complete project (code, JSON data file, database) will live on the Linux server at `/var/www/bridleway-log/`.**  
**You will develop on Windows but the final code must work when copied to `/var/www/bridleway-log/` on the Linux server.**

Your task is to implement **Bridleway Log** \- the initial version of the **Bike Path Coverage Map** application described in the SRS below, using the specified stack.

## **Technology stack**

Implement using:

* Backend:  
  * Python 3.x  
  * FastAPI  
  * Uvicorn (or Gunicorn+Uvicorn workers in production)  
* Database:  
  * PostgreSQL  
  * PostGIS extension for spatial operations  
* Frontend:  
  * HTML \+ CSS  
  * Vanilla JavaScript  
  * Leaflet for maps  
* Deployment:  
  * Docker Compose to run from `/var/www/bridleway-log/` on the Linux server:  
    * `web`: FastAPI backend (also serving static frontend assets) on port 6080  
    * `db`: Postgres \+ PostGIS  
    * Data volume mounted at `/data/` inside containers (maps to `/var/www/bridleway-log/data/` on host)

## **Requirements (from SRS v2.0)**

**File locations on Linux server:**

text

`/var/www/bridleway-log/`

`├── docker-compose.yml`

`├── .env`

`├── data/`

`│   └── Public-Rights-of-Way-Jan-2022-JSON-1.json  ← Your attached JSON file`

`├── backend/`

`└── frontend/`

Implement the **first iteration** with focus on:

1. Path import and storage  
2. API for paths and basic stats  
3. Minimal Leaflet map frontend with filters  
4. Docker Compose for deployment at `/var/www/bridleway-log/` on Linux server

## **Core features to implement now**

1. **Bike path model and import**  
   * Import script reads JSON from `/data/Public-Rights-of-Way-Jan-2022-JSON-1.json` on Linux server  
   * Assigns `area` parameter (e.g. `"CMBC RoW Network"`)  
   * Stores paths in PostGIS database with fields:  
     * `id`, `source_fid`, `route_code`, `name`, `path_type`, `area`, `geometry`, `length_km`  
2. **API endpoints**  
   * `GET /api/paths?area=...&path_type=...` → GeoJSON FeatureCollection  
   * `GET /api/stats` → path counts and lengths  
   * `GET /api/areas` → distinct area names  
3. **Frontend** served from FastAPI at `http://192.168.178.22:6080/`  
   * Leaflet map with path rendering  
   * Area and path type filters  
   * Unit toggle (metric/imperial)  
   * Path popups and stats panel

## **Deployment instructions in README**

The README must include **exact commands** for the Linux server:

bash

*`# On Linux server at 192.168.178.22:`*

`sudo mkdir -p /var/www/bridleway-log/data`

`sudo chown $USER:$USER /var/www/bridleway-log -R`

*`# Copy your JSON file to /var/www/bridleway-log/data/Calderdale-JSON.json`*

`cd /var/www/bridleway-log/`

`cp .env.example .env`

*`# Edit .env with DB password, etc.`*

`docker compose up -d`

`docker compose run --rm web python scripts/import_paths.py --file /data/Calderdale-JSON.json --area "CMBC RoW Network"`

*`# Access at http://192.168.178.22:6080/`*

## **Project structure on Linux server**

text

`/var/www/bridleway-log/`

`├── backend/`

`│   ├── app/`

`│   │   ├── main.py`

`│   │   ├── config.py`

`│   │   ├── db.py`

`│   │   ├── models.py`

`│   │   ├── schemas.py`

`│   │   └── api/`

`│   │       ├── __init__.py`

`│   │       ├── paths.py`

`│   │       └── stats.py`

`│   ├── scripts/`

`│   │   └── import_paths.py`

`│   ├── requirements.txt`

`│   └── Dockerfile`

`├── frontend/`

`│   ├── index.html`

`│   └── assets/`

`│       ├── js/`

`│       │   └── main.js`

`│       └── css/`

`│           └── styles.css`

`├── data/`

`│   └── Calderdale-JSON.json  ← Mounted to /data/ in Docker`

`├── docker-compose.yml`

`├── .env.example`

`├── .gitignore`

`└── README.md`

## **Output format**

1. Show the **complete Linux server directory structure** at `/var/www/bridleway-log/`  
2. Provide **all key files** with Linux server paths:  
   * `/var/www/bridleway-log/docker-compose.yml` (port 6080, data volume)  
   * `/var/www/bridleway-log/backend/Dockerfile`  
   * Backend Python files  
   * Frontend files  
   * `/var/www/bridleway-log/.env.example`  
3. **README.md** with **exact copy/paste commands** for Linux server setup  
4. **Windows development workflow**: How to test locally before copying to Linux server

## **Environment variables in `.env.example`**

text

`POSTGRES_USER=bridleway`

`POSTGRES_PASSWORD=changeme`

`POSTGRES_DB=bridleway_log`

`JSON_IMPORT_PATH=/data/Calderdale-JSON.json`

`DEFAULT_AREA=CMBC RoW Network`

**Avoid over‑engineering; prioritise a working, minimal implementation for `/var/www/bridleway-log/` on the Linux server that I can iterate on later to add GPX upload and real coverage logic.**

