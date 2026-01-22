import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://bridleway:changeme@localhost:5432/bridleway_log"
)
