from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from geoalchemy2 import Geometry
from datetime import datetime
from app.db import Base


class Path(Base):
    __tablename__ = "paths"

    id = Column(Integer, primary_key=True, index=True)
    source_fid = Column(String, index=True)
    route_code = Column(String, index=True)
    name = Column(String)
    path_type = Column(String, index=True)
    area = Column(String, index=True)
    geometry = Column(Geometry("LINESTRING", srid=4326))
    length_km = Column(Float)

    # Coverage fields (iteration 2)
    is_ridden = Column(Boolean, default=False, index=True)
    coverage_fraction = Column(Float, default=0.0)
    last_ridden_date = Column(DateTime, nullable=True)


class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String(64), unique=True, index=True)  # SHA-256 for deduplication
    date_recorded = Column(DateTime, nullable=True)
    distance_km = Column(Float, default=0.0)
    elevation_gain_m = Column(Float, nullable=True)
    geometry = Column(Geometry("MULTILINESTRING", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)
