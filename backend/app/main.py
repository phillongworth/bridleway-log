from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.db import engine, Base
from app.api import paths, stats

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bridleway Log", version="1.0.0")

# API routes
app.include_router(paths.router, prefix="/api", tags=["paths"])
app.include_router(stats.router, prefix="/api", tags=["stats"])

# Serve frontend static files
app.mount("/assets", StaticFiles(directory="/app/static/assets"), name="assets")


@app.get("/")
async def root():
    return FileResponse("/app/static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}
