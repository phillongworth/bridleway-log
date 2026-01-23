-- Migration: Add rides table and coverage columns to paths
-- Version: 2.0.0
-- Date: 2026-01-22

-- Create rides table for storing GPX track data
CREATE TABLE IF NOT EXISTS rides (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    date_recorded TIMESTAMP,
    distance_km FLOAT DEFAULT 0.0,
    elevation_gain_m FLOAT,
    geometry GEOMETRY(MULTILINESTRING, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for rides table
CREATE INDEX IF NOT EXISTS idx_rides_file_hash ON rides(file_hash);
CREATE INDEX IF NOT EXISTS idx_rides_date_recorded ON rides(date_recorded);
CREATE INDEX IF NOT EXISTS idx_rides_geometry ON rides USING GIST(geometry);

-- Add coverage columns to paths table
ALTER TABLE paths ADD COLUMN IF NOT EXISTS is_ridden BOOLEAN DEFAULT FALSE;
ALTER TABLE paths ADD COLUMN IF NOT EXISTS coverage_fraction FLOAT DEFAULT 0.0;
ALTER TABLE paths ADD COLUMN IF NOT EXISTS last_ridden_date TIMESTAMP;

-- Create index on is_ridden for faster filtering
CREATE INDEX IF NOT EXISTS idx_paths_is_ridden ON paths(is_ridden);

-- Verify migration
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rides') THEN
        RAISE NOTICE 'Migration complete: rides table created';
    ELSE
        RAISE EXCEPTION 'Migration failed: rides table not created';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'paths' AND column_name = 'is_ridden') THEN
        RAISE NOTICE 'Migration complete: coverage columns added to paths';
    ELSE
        RAISE EXCEPTION 'Migration failed: coverage columns not added';
    END IF;
END $$;
