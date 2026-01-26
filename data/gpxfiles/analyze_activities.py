#!/usr/bin/env python3
"""
Analyze activities.csv and match with GPX/FIT files.
"""

import csv
import os
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path('/var/www/bridleway-log/data/gpxfiles')
ACTIVITIES_DIR = BASE_DIR / 'activities'
CSV_FILE = BASE_DIR / 'activities.csv'

def analyze():
    # Parse CSV to get expected files
    csv_files = {}
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename']
            # Extract just the filename part (remove 'activities/' prefix)
            if filename.startswith('activities/'):
                filename = filename[11:]
            csv_files[filename] = {
                'activity_id': row['Activity ID'],
                'date': row['Activity Date'],
                'name': row['Activity Name'],
                'type': row['Activity Type'],
                'distance': row['Distance']
            }

    print(f"CSV entries: {len(csv_files)}")

    # Count file types in CSV
    csv_types = defaultdict(int)
    for f in csv_files.keys():
        if f.endswith('.fit.gz'):
            csv_types['fit.gz'] += 1
        elif f.endswith('.gpx.gz'):
            csv_types['gpx.gz'] += 1
        elif f.endswith('.gpx'):
            csv_types['gpx'] += 1
        else:
            csv_types['other'] += 1

    print(f"\nCSV file types:")
    for t, count in sorted(csv_types.items()):
        print(f"  .{t}: {count}")

    # Get actual files in directory
    actual_files = set()
    for f in ACTIVITIES_DIR.iterdir():
        if f.is_file():
            actual_files.add(f.name)

    print(f"\nActual files in directory: {len(actual_files)}")

    # Count actual file types
    actual_types = defaultdict(int)
    for f in actual_files:
        if f.endswith('.fit.gz'):
            actual_types['fit.gz'] += 1
        elif f.endswith('.gpx.gz'):
            actual_types['gpx.gz'] += 1
        elif f.endswith('.gpx'):
            actual_types['gpx'] += 1
        else:
            actual_types['other'] += 1

    print(f"\nActual file types:")
    for t, count in sorted(actual_types.items()):
        print(f"  .{t}: {count}")

    # Find matches and mismatches
    csv_file_set = set(csv_files.keys())

    matched = csv_file_set & actual_files
    in_csv_not_on_disk = csv_file_set - actual_files
    on_disk_not_in_csv = actual_files - csv_file_set

    print(f"\n--- Matching Results ---")
    print(f"Matched (in CSV and on disk): {len(matched)}")
    print(f"In CSV but not on disk: {len(in_csv_not_on_disk)}")
    print(f"On disk but not in CSV (unmatched): {len(on_disk_not_in_csv)}")

    # Breakdown matched files by type
    matched_types = defaultdict(int)
    for f in matched:
        if f.endswith('.fit.gz'):
            matched_types['fit.gz'] += 1
        elif f.endswith('.gpx.gz'):
            matched_types['gpx.gz'] += 1
        elif f.endswith('.gpx'):
            matched_types['gpx'] += 1

    print(f"\nMatched files by type:")
    for t, count in sorted(matched_types.items()):
        print(f"  .{t}: {count}")

    # Show some examples of unmatched files
    if on_disk_not_in_csv:
        print(f"\nSample unmatched files (first 10):")
        for f in sorted(on_disk_not_in_csv)[:10]:
            print(f"  {f}")

    if in_csv_not_on_disk:
        print(f"\nSample files in CSV but missing from disk (first 10):")
        for f in sorted(in_csv_not_on_disk)[:10]:
            print(f"  {f}")

    # Return data for further processing
    return {
        'matched': matched,
        'unmatched': on_disk_not_in_csv,
        'missing': in_csv_not_on_disk,
        'csv_data': csv_files
    }

if __name__ == '__main__':
    analyze()
