import os
from pathlib import Path

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SYNERGY_DIR = BASE_DIR / "synergy-panorama"
S5P_PAL_DIR = BASE_DIR / "data" / "s5p_pal"
RESULTS_DIR = BASE_DIR / "results"

# Ensure output directories exist
for sub in ["nc", "stats", "quicklooks"]:
    (RESULTS_DIR / sub).mkdir(parents=True, exist_ok=True)
S5P_PAL_DIR.mkdir(parents=True, exist_ok=True)

# S5P PAL STAC API Endpoint
S5P_PAL_STAC_URL = "https://data-portal.s5p-pal.com/api/stac/v1"

# Default Spatial Rebinning Settings
DEFAULT_RES_LAT = 0.1  # degrees
DEFAULT_RES_LON = 0.1  # degrees
DEFAULT_BBOX = [-180.0, -90.0, 180.0, 90.0]  # [min_lon, min_lat, max_lon, max_lat]
DEFAULT_METHOD = "mean"

# Default Variable Names in NetCDF files (Update according to specific product versions)
GRASP_CONFIG = {
    "lat_var": "latitude",
    "lon_var": "longitude",
    "val_var": "aod_550",
    "qa_var": "quality_flag",
    "qa_threshold": 1
}

S5P_CONFIG = {
    "group": "PRODUCT",
    "lat_var": "latitude",
    "lon_var": "longitude",
    "val_var": "aerosol_index_354_388",
    "qa_var": "qa_value",
    "qa_threshold": 0.5
}