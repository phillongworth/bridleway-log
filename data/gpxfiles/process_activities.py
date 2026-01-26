#!/usr/bin/env python3
"""
Process activities:
1. Move unmatched files to 'unmatched' folder
2. Convert matched .fit.gz files to .gpx
3. Decompress matched .gpx.gz files
"""

import csv
import gzip
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path('/var/www/bridleway-log/data/gpxfiles')
ACTIVITIES_DIR = BASE_DIR / 'activities'
UNMATCHED_DIR = BASE_DIR / 'unmatched'
CSV_FILE = BASE_DIR / 'activities.csv'

# Try to import fitdecode - will be needed for FIT conversion
try:
    import fitdecode
    HAS_FITDECODE = True
except ImportError:
    HAS_FITDECODE = False
    print("WARNING: fitdecode not installed. Install with: pip install fitdecode")
    print("FIT files will not be converted.")


def get_csv_files():
    """Parse CSV and return set of expected filenames."""
    csv_files = set()
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename']
            if filename and filename.startswith('activities/'):
                filename = filename[11:]  # Remove 'activities/' prefix
                if filename:  # Skip empty filenames
                    csv_files.add(filename)
    return csv_files


def get_actual_files():
    """Get set of actual files in activities directory."""
    return {f.name for f in ACTIVITIES_DIR.iterdir() if f.is_file()}


def move_unmatched_files(unmatched):
    """Move unmatched files to unmatched directory."""
    UNMATCHED_DIR.mkdir(exist_ok=True)

    moved = 0
    errors = 0

    for filename in unmatched:
        src = ACTIVITIES_DIR / filename
        dst = UNMATCHED_DIR / filename
        try:
            shutil.move(str(src), str(dst))
            moved += 1
        except Exception as e:
            print(f"  Error moving {filename}: {e}")
            errors += 1

    return moved, errors


def decompress_gpx_gz(filepath):
    """Decompress a .gpx.gz file to .gpx"""
    output_path = filepath.with_suffix('')  # Remove .gz

    try:
        with gzip.open(filepath, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        # Remove original .gz file
        filepath.unlink()
        return True, output_path
    except Exception as e:
        return False, str(e)


def fit_to_gpx(fit_path, gpx_path):
    """Convert a FIT file to GPX format."""
    if not HAS_FITDECODE:
        return False, "fitdecode not installed"

    try:
        # Read FIT file
        points = []

        with fitdecode.FitReader(fit_path) as fit:
            for frame in fit:
                if isinstance(frame, fitdecode.FitDataMessage):
                    if frame.name == 'record':
                        point = {}

                        # Get position
                        lat = frame.get_value('position_lat')
                        lon = frame.get_value('position_long')

                        if lat is not None and lon is not None:
                            # Convert semicircles to degrees
                            point['lat'] = lat * (180 / 2**31)
                            point['lon'] = lon * (180 / 2**31)

                            # Get optional fields
                            alt = frame.get_value('altitude')
                            if alt is not None:
                                point['ele'] = alt

                            timestamp = frame.get_value('timestamp')
                            if timestamp is not None:
                                point['time'] = timestamp

                            points.append(point)

        if not points:
            return False, "No GPS points found in FIT file"

        # Generate GPX XML
        gpx_content = generate_gpx(points)

        with open(gpx_path, 'w', encoding='utf-8') as f:
            f.write(gpx_content)

        return True, gpx_path

    except Exception as e:
        return False, str(e)


def generate_gpx(points):
    """Generate GPX XML from list of points."""
    gpx = ['<?xml version="1.0" encoding="UTF-8"?>']
    gpx.append('<gpx version="1.1" creator="activities_processor"')
    gpx.append('  xmlns="http://www.topografix.com/GPX/1/1"')
    gpx.append('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    gpx.append('  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">')
    gpx.append('  <trk>')
    gpx.append('    <name>Activity</name>')
    gpx.append('    <trkseg>')

    for pt in points:
        lat = pt['lat']
        lon = pt['lon']
        gpx.append(f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}">')

        if 'ele' in pt:
            gpx.append(f'        <ele>{pt["ele"]:.1f}</ele>')

        if 'time' in pt:
            if isinstance(pt['time'], datetime):
                time_str = pt['time'].strftime('%Y-%m-%dT%H:%M:%SZ')
            else:
                time_str = str(pt['time'])
            gpx.append(f'        <time>{time_str}</time>')

        gpx.append('      </trkpt>')

    gpx.append('    </trkseg>')
    gpx.append('  </trk>')
    gpx.append('</gpx>')

    return '\n'.join(gpx)


def convert_fit_gz(filepath):
    """Decompress and convert a .fit.gz file to .gpx"""
    # First decompress
    fit_path = filepath.with_suffix('')  # Remove .gz -> .fit
    gpx_path = fit_path.with_suffix('.gpx')  # .fit -> .gpx

    try:
        # Decompress to temporary .fit file
        with gzip.open(filepath, 'rb') as f_in:
            with open(fit_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Convert FIT to GPX
        success, result = fit_to_gpx(fit_path, gpx_path)

        # Clean up .fit file
        if fit_path.exists():
            fit_path.unlink()

        if success:
            # Remove original .fit.gz file
            filepath.unlink()
            return True, gpx_path
        else:
            return False, result

    except Exception as e:
        # Clean up on error
        if fit_path.exists():
            fit_path.unlink()
        return False, str(e)


def main():
    print("=" * 60)
    print("Activities File Processor")
    print("=" * 60)

    # Get file lists
    csv_files = get_csv_files()
    actual_files = get_actual_files()

    matched = csv_files & actual_files
    unmatched = actual_files - csv_files

    print(f"\nFiles in CSV: {len(csv_files)}")
    print(f"Files on disk: {len(actual_files)}")
    print(f"Matched: {len(matched)}")
    print(f"Unmatched (to move): {len(unmatched)}")

    # Categorize matched files
    matched_gpx = [f for f in matched if f.endswith('.gpx')]
    matched_gpx_gz = [f for f in matched if f.endswith('.gpx.gz')]
    matched_fit_gz = [f for f in matched if f.endswith('.fit.gz')]

    print(f"\nMatched files breakdown:")
    print(f"  .gpx files (no action needed): {len(matched_gpx)}")
    print(f"  .gpx.gz files (to decompress): {len(matched_gpx_gz)}")
    print(f"  .fit.gz files (to convert): {len(matched_fit_gz)}")

    # Step 1: Move unmatched files
    print(f"\n--- Step 1: Moving {len(unmatched)} unmatched files ---")
    if unmatched:
        moved, errors = move_unmatched_files(unmatched)
        print(f"  Moved: {moved}, Errors: {errors}")
    else:
        print("  No unmatched files to move.")

    # Step 2: Decompress .gpx.gz files
    print(f"\n--- Step 2: Decompressing {len(matched_gpx_gz)} .gpx.gz files ---")
    gpx_gz_success = 0
    gpx_gz_errors = 0
    for filename in matched_gpx_gz:
        filepath = ACTIVITIES_DIR / filename
        success, result = decompress_gpx_gz(filepath)
        if success:
            gpx_gz_success += 1
        else:
            print(f"  Error decompressing {filename}: {result}")
            gpx_gz_errors += 1
    print(f"  Decompressed: {gpx_gz_success}, Errors: {gpx_gz_errors}")

    # Step 3: Convert .fit.gz files
    print(f"\n--- Step 3: Converting {len(matched_fit_gz)} .fit.gz files ---")
    if not HAS_FITDECODE:
        print("  SKIPPED: fitdecode library not installed")
        print("  Install with: pip install fitdecode")
        print("  Then re-run this script.")
    else:
        fit_success = 0
        fit_errors = 0
        for i, filename in enumerate(matched_fit_gz, 1):
            if i % 50 == 0 or i == len(matched_fit_gz):
                print(f"  Processing {i}/{len(matched_fit_gz)}...")
            filepath = ACTIVITIES_DIR / filename
            success, result = convert_fit_gz(filepath)
            if success:
                fit_success += 1
            else:
                print(f"  Error converting {filename}: {result}")
                fit_errors += 1
        print(f"  Converted: {fit_success}, Errors: {fit_errors}")

    # Summary
    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)

    # Show final state
    remaining_files = list(ACTIVITIES_DIR.iterdir())
    gpx_count = len([f for f in remaining_files if f.name.endswith('.gpx')])
    other_count = len([f for f in remaining_files if not f.name.endswith('.gpx')])

    print(f"\nFinal state of activities folder:")
    print(f"  .gpx files: {gpx_count}")
    print(f"  Other files: {other_count}")

    if UNMATCHED_DIR.exists():
        unmatched_count = len(list(UNMATCHED_DIR.iterdir()))
        print(f"\nUnmatched folder: {unmatched_count} files")


if __name__ == '__main__':
    main()
