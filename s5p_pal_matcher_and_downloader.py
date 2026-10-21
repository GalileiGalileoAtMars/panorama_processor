#!/usr/bin/env python3
"""
Automated S5P PAL Downloader matching local GRASP Synergy files.
Extracts temporal and spatial bounds from GRASP NetCDF files and queries the S5P PAL STAC API.
"""

import os
import re
import glob
import argparse
import datetime
import requests
import numpy as np
import xarray as xr
from pathlib import Path
from tqdm import tqdm
from pystac_client import Client

from config import SYNERGY_DIR, S5P_PAL_DIR, S5P_PAL_STAC_URL


def extract_metadata_from_grasp(nc_file: Path):
    """
    Extracts sensing date/time and bounding box from a GRASP Synergy NetCDF file.
    Falls back to filename parsing if global attributes are missing.
    """
    try:
        with xr.open_dataset(nc_file) as ds:
            # Extract spatial bounding box
            lat_name = "latitude" if "latitude" in ds else "lat"
            lon_name = "longitude" if "longitude" in ds else "lon"
            
            lats = ds[lat_name].values
            lons = ds[lon_name].values
            bbox = [
                float(np.nanmin(lons)),
                float(np.nanmin(lats)),
                float(np.nanmax(lons)),
                float(np.nanmax(lats))
            ]

            # Extract timestamp from attributes or filename (e.g., *20230515T120000*)
            if "time_coverage_start" in ds.attrs:
                t_start = datetime.datetime.fromisoformat(ds.attrs["time_coverage_start"].replace("Z", ""))
            else:
                match = re.search(r"(20\d{2})(\d{2})(\d{2})", nc_file.name)
                if match:
                    t_start = datetime.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                else:
                    raise ValueError(f"Could not parse timestamp from {nc_file.name}")

            # Search window: +/- 3 hours around synergy observation or full day
            start_window = t_start.replace(hour=0, minute=0, second=0).isoformat() + "Z"
            end_window = t_start.replace(hour=23, minute=59, second=59).isoformat() + "Z"

            return f"{start_window}/{end_window}", bbox

    except Exception as e:
        print(f"[WARNING] Failed to read metadata from {nc_file.name}: {e}")
        return None, None


def download_file(url: str, dest_path: Path, api_key: str = None):
    """Streams download with progress bar."""
    if dest_path.exists():
        print(f"  [SKIP] {dest_path.name} already exists.")
        return

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    response = requests.get(url, headers=headers, stream=True, timeout=60)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    with open(dest_path, "wb") as f, tqdm(
        desc=dest_path.name,
        total=total_size,
        unit="iB",
        unit_scale=True,
        unit_divisor=1024,
        leave=False
    ) as bar:
        for data in response.iter_content(chunk_size=8192):
            size = f.write(data)
            bar.update(size)


def main():
    parser = argparse.ArgumentParser(description="Download S5P PAL files matching GRASP Synergy datasets.")
    parser.add_argument("--synergy-dir", type=Path, default=SYNERGY_DIR, help="Directory with GRASP .nc files")
    parser.add_argument("--output-dir", type=Path, default=S5P_PAL_DIR, help="Output directory for S5P PAL files")
    parser.add_argument("--product", type=str, default="L2__AER_AI", help="S5P PAL collection/product ID")
    parser.add_argument("--api-key", type=str, default=os.environ.get("S5P_PAL_API_KEY"), help="Optional API Key")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    grasp_files = sorted(list(args.synergy_dir.rglob("*.nc")))

    if not grasp_files:
        print(f"[ERROR] No GRASP Synergy NetCDF files found in {args.synergy_dir}.")
        print("Please run './download_script.sh' first.")
        return

    print(f"Found {len(grasp_files)} GRASP Synergy files. Connecting to S5P PAL STAC catalogue...")
    
    try:
        catalog = Client.open(S5P_PAL_STAC_URL)
    except Exception as e:
        print(f"[ERROR] Could not connect to STAC API at {S5P_PAL_STAC_URL}: {e}")
        return

    queried_dates = set()

    for g_file in grasp_files:
        time_range, bbox = extract_metadata_from_grasp(g_file)
        if not time_range:
            continue

        date_key = time_range.split("T")[0]
        if date_key in queried_dates:
            continue
        queried_dates.add(date_key)

        print(f"\nQuerying S5P PAL ({args.product}) for Date: {date_key} | BBOX: {[round(x, 2) for x in bbox]}")
        
        try:
            search = catalog.search(
                collections=[args.product],
                datetime=time_range,
                bbox=bbox
            )
            items = list(search.get_items())
            print(f"  -> Found {len(items)} matching S5P PAL orbit file(s).")

            for item in items:
                # Find NetCDF asset link
                for asset_key, asset in item.assets.items():
                    if asset.href.endswith(".nc"):
                        filename = Path(asset.href).name
                        dest = args.output_dir / filename
                        download_file(asset.href, dest, args.api_key)

        except Exception as e:
            print(f"  [WARNING] Query failed for {date_key}: {e}")

    print("\nS5P PAL matching and download complete!")


if __name__ == "__main__":
    main()