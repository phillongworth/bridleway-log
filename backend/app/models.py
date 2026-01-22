from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
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
