#!/usr/bin/env python3
"""
Main execution pipeline for daily GRASP Synergy & S5P PAL comparison.
Supports user-defined spatial rebinning, NetCDF export, CSV metrics, and 4-panel quicklooks.
"""

import re
import argparse
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.stats import pearsonr, linregress
from pathlib import Path

from config import (
    SYNERGY_DIR, S5P_PAL_DIR, RESULTS_DIR,
    DEFAULT_RES_LAT, DEFAULT_RES_LON, DEFAULT_BBOX, DEFAULT_METHOD,
    GRASP_CONFIG, S5P_CONFIG
)
from rebinning import SpatialRebinner


def find_files_for_date(directory: Path, date_str: str):
    """Finds NetCDF files matching YYYY-MM-DD or YYYYMMDD in filename."""
    compact_date = date_str.replace("-", "")
    matched = []
    for f in directory.rglob("*.nc"):
        if compact_date in f.name or date_str in f.name:
            matched.append(f)
    return sorted(matched)


def load_daily_swaths(files: list, cfg: dict, is_s5p: bool = False):
    """Loads and concatenates swath coordinates and values from multiple orbit files."""
    all_lats, all_lons, all_vals = [], [], []
    
    for f in files:
        try:
            group = cfg.get("group") if is_s5p else None
            with xr.open_dataset(f, group=group) as ds:
                lats = ds[cfg["lat_var"]].values
                lons = ds[cfg["lon_var"]].values
                vals = ds[cfg["val_var"]].values

                # Apply Quality Flag filtering if present
                if cfg["qa_var"] in ds:
                    qa = ds[cfg["qa_var"]].values
                    vals = np.where(qa >= cfg["qa_threshold"], vals, np.nan)

                all_lats.append(lats.ravel())
                all_lons.append(lons.ravel())
                all_vals.append(vals.ravel())
        except Exception as e:
            print(f"  [WARNING] Skipping {f.name} due to read error: {e}")

    if not all_vals:
        return np.array([]), np.array([]), np.array([])

    return np.concatenate(all_lats), np.concatenate(all_lons), np.concatenate(all_vals)


def generate_synthetic_demo_data(bbox: list):
    """Generates realistic synthetic swath data if user runs pipeline before downloading files."""
    print("  [INFO] Generating synthetic daily demonstration swaths for testing...")
    np.random.seed(42)
    n_samples = 80000
    lons = np.random.uniform(bbox[0], bbox[2], n_samples)
    lats = np.random.uniform(bbox[1], bbox[3], n_samples)
    
    # Create spatial plume pattern
    plume = np.exp(-((lons - np.mean(bbox[::2]))**2 + (lats - np.mean(bbox[1::2]))**2) / 150.0)
    grasp_vals = 0.15 + 1.2 * plume + np.random.normal(0, 0.08, n_samples)
    s5p_vals = 0.10 + 1.15 * plume + np.random.normal(0, 0.12, n_samples)
    
    return (lats, lons, np.clip(grasp_vals, 0, None)), (lats, lons, np.clip(s5p_vals, 0, None))


def save_collocated_netcdf(rebinner: SpatialRebinner, date_str: str, g_res: tuple, s_res: tuple):
    """Exports the rebinned daily comparison dataset to NetCDF4."""
    g_val, g_std, g_cnt = g_res
    s_val, s_std, s_cnt = s_res
    diff = g_val - s_val

    ds = xr.Dataset(
        data_vars={
            "grasp_aod_550": (("lat", "lon"), g_val, {"units": "1", "long_name": "Rebinned GRASP Synergy AOD"}),
            "grasp_aod_std": (("lat", "lon"), g_std, {"units": "1", "long_name": "GRASP AOD Intra-cell StdDev"}),
            "s5p_pal_val": (("lat", "lon"), s_val, {"units": "1", "long_name": "Rebinned S5P PAL Product"}),
            "s5p_pal_std": (("lat", "lon"), s_std, {"units": "1", "long_name": "S5P PAL Intra-cell StdDev"}),
            "absolute_difference": (("lat", "lon"), diff, {"units": "1", "long_name": "Difference (GRASP - S5P PAL)"}),
            "pixel_count": (("lat", "lon"), np.minimum(g_cnt, s_cnt), {"long_name": "Valid Collocated Pixel Count"})
        },
        coords={
            "lat": ("lat", rebinner.lat_centers, {"units": "degrees_north"}),
            "lon": ("lon", rebinner.lon_centers, {"units": "degrees_east"}),
        },
        attrs={
            "title": f"Collocated GRASP Synergy and S5P PAL Daily Rebinned Product ({date_str})",
            "spatial_resolution": f"{rebinner.res_lat} deg lat x {rebinner.res_lon} deg lon",
            "aggregation_method": rebinner.method,
            "bounding_box": str(
                [rebinner.min_lon, rebinner.min_lat, rebinner.max_lon, rebinner.max_lat]
            )
        }
    )

    compact_date = date_str.replace("-", "")
    res_tag = f"res{rebinner.res_lat}x{rebinner.res_lon}"
    out_path = RESULTS_DIR / "nc" / f"collocated_GRASP_S5PPAL_{compact_date}_{res_tag}.nc"
    ds.to_netcdf(out_path)
    print(f"  -> Saved Rebinned NetCDF: {out_path}")
    return out_path


def compute_and_save_stats(date_str: str, g_val: np.ndarray, s_val: np.ndarray, rebinner: SpatialRebinner):
    """Computes statistical comparison metrics and saves to CSV."""
    valid = np.isfinite(g_val) & np.isfinite(s_val)
    x = g_val[valid]
    y = s_val[valid]
    n_pts = len(x)

    if n_pts < 3:
        print("  [WARNING] Insufficient overlapping grid cells for statistical analysis.")
        return None

    r_val, p_val = pearsonr(x, y)
    rmse = float(np.sqrt(np.mean((x - y) ** 2)))
    mbe = float(np.mean(x - y))
    slope, intercept, _, _, _ = linregress(x, y)

    stats_dict = {
        "date": date_str,
        "res_lat": rebinner.res_lat,
        "res_lon": rebinner.res_lon,
        "method": rebinner.method,
        "N_collocated_cells": n_pts,
        "pearson_r": round(r_val, 4),
        "p_value": float(f"{p_val:.2e}"),
        "rmse": round(rmse, 4),
        "mean_bias_error": round(mbe, 4),
        "slope": round(slope, 4),
        "intercept": round(intercept, 4)
    }

    compact_date = date_str.replace("-", "")
    csv_path = RESULTS_DIR / "stats" / f"daily_stats_{compact_date}.csv"
    pd.DataFrame([stats_dict]).to_csv(csv_path, index=False)
    print(f"  -> Saved Statistical Summary: {csv_path}")
    return stats_dict


def generate_quicklook(date_str: str, rebinner: SpatialRebinner, g_val: np.ndarray, s_val: np.ndarray, stats: dict):
    """Generates a 4-panel daily comparison quicklook PNG."""
    fig = plt.figure(figsize=(15, 11), dpi=150)
    fig.suptitle(
        f"Daily Synergy Comparison: GRASP PANORAMA vs. S5P PAL ({date_str})\n"
        f"Grid Resolution: {rebinner.res_lat}° x {rebinner.res_lon}° ({rebinner.method.capitalize()})",
        fontsize=14, fontweight="bold"
    )

    extent = [rebinner.min_lon, rebinner.max_lon, rebinner.min_lat, rebinner.max_lat]
    vmin = np.nanpercentile(np.concatenate([g_val.ravel(), s_val.ravel()]), 5)
    vmax = np.nanpercentile(np.concatenate([g_val.ravel(), s_val.ravel()]), 95)

    # 1. GRASP Map
    ax1 = fig.add_subplot(2, 2, 1, projection=ccrs.PlateCarree())
    ax1.set_extent(extent, crs=ccrs.PlateCarree())
    ax1.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax1.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.5)
    im1 = ax1.pcolormesh(rebinner.lon_edges, rebinner.lat_edges, g_val, cmap="viridis", vmin=vmin, vmax=vmax)
    plt.colorbar(im1, ax=ax1, orientation="horizontal", pad=0.06, label="GRASP Synergy Value")
    ax1.set_title("1. Rebinned GRASP PANORAMA")

    # 2. S5P PAL Map
    ax2 = fig.add_subplot(2, 2, 2, projection=ccrs.PlateCarree())
    ax2.set_extent(extent, crs=ccrs.PlateCarree())
    ax2.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax2.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.5)
    im2 = ax2.pcolormesh(rebinner.lon_edges, rebinner.lat_edges, s_val, cmap="viridis", vmin=vmin, vmax=vmax)
    plt.colorbar(im2, ax=ax2, orientation="horizontal", pad=0.06, label="S5P PAL Value")
    ax2.set_title("2. Rebinned S5P PAL")

    # 3. Difference Map (GRASP - S5P)
    diff = g_val - s_val
    max_abs_diff = np.nanpercentile(np.abs(diff), 95)
    ax3 = fig.add_subplot(2, 2, 3, projection=ccrs.PlateCarree())
    ax3.set_extent(extent, crs=ccrs.PlateCarree())
    ax3.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax3.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.5)
    im3 = ax3.pcolormesh(
        rebinner.lon_edges, rebinner.lat_edges, diff,
        cmap="RdBu_r", vmin=-max_abs_diff, vmax=max_abs_diff
    )
    plt.colorbar(im3, ax=ax3, orientation="horizontal", pad=0.06, label="Difference (GRASP - S5P PAL)")
    ax3.set_title("3. Spatial Absolute Difference")

    # 4. Scatter / Density Plot
    ax4 = fig.add_subplot(2, 2, 4)
    valid = np.isfinite(g_val) & np.isfinite(s_val)
    x, y = g_val[valid], s_val[valid]

    if len(x) > 0:
        hb = ax4.hexbin(x, y, gridsize=40, cmap="inferno", mincnt=1)
        plt.colorbar(hb, ax=ax4, label="Grid Cell Count")
        
        lim_min = min(np.min(x), np.min(y))
        lim_max = max(np.max(x), np.max(y))
        ax4.plot([lim_min, lim_max], [lim_min, lim_max], "k--", lw=1.5, label="1:1 Line")

        if stats:
            reg_y = stats["slope"] * np.array([lim_min, lim_max]) + stats["intercept"]
            ax4.plot([lim_min, lim_max], reg_y, "r-", lw=1.5, label="Linear Fit")
            stats_text = (
                f"N = {stats['N_collocated_cells']}\n"
                f"R = {stats['pearson_r']:.3f}\n"
                f"RMSE = {stats['rmse']:.3f}\n"
                f"Bias = {stats['mean_bias_error']:.3f}\n"
                f"Y = {stats['slope']:.2f}X + {stats['intercept']:.2f}"
            )
            ax4.text(
                0.05, 0.95, stats_text, transform=ax4.transAxes,
                verticalalignment="top", bbox=dict(boxstyle="round", facecolor="white", alpha=0.85)
            )
        ax4.legend(loc="lower right")

    ax4.set_xlabel("GRASP Synergy Rebinned Value")
    ax4.set_ylabel("S5P PAL Rebinned Value")
    ax4.set_title("4. Collocated Grid Cell Correlation")
    ax4.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout(rect=[0, 0.02, 1, 0.94])
    compact_date = date_str.replace("-", "")
    res_tag = f"res{rebinner.res_lat}x{rebinner.res_lon}"
    out_img = RESULTS_DIR / "quicklooks" / f"quicklook_{compact_date}_{res_tag}.png"
    plt.savefig(out_img)
    plt.close(fig)
    print(f"  -> Saved 4-Panel Quicklook: {out_img}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Daily Synergy & S5P PAL Spatial Rebinning and Comparison."
    )
    parser.add_argument("--date", type=str, default="2023-06-12", help="Target date YYYY-MM-DD")
    parser.add_argument("--res-lat", type=float, default=DEFAULT_RES_LAT, help="Latitude grid resolution (deg)")
    parser.add_argument("--res-lon", type=float, default=DEFAULT_RES_LON, help="Longitude grid resolution (deg)")
    parser.add_argument(
        "--bbox", type=float, nargs=4, default=DEFAULT_BBOX,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Spatial bounding box [min_lon min_lat max_lon max_lat]"
    )
    parser.add_argument(
        "--method", type=str, choices=["mean", "median"], default=DEFAULT_METHOD,
        help="Spatial aggregation method for rebinning"
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Prompt user interactively for spatial rebinning parameters"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Interactive user input option for spatial rebinning
    if args.interactive:
        print("\n--- Interactive Spatial Rebinning Configuration ---")
        try:
            res_in = input(f"Enter grid resolution in degrees (lat,lon) [default {args.res_lat},{args.res_lon}]: ").strip()
            if res_in:
                args.res_lat, args.res_lon = [float(x) for x in res_in.split(",")]
            bbox_in = input(f"Enter bounding box 'min_lon min_lat max_lon max_lat' [default {args.bbox}]: ").strip()
            if bbox_in:
                args.bbox = [float(x) for x in bbox_in.split()]
            method_in = input(f"Enter aggregation method (mean/median) [default {args.method}]: ").strip()
            if method_in in ["mean", "median"]:
                args.method = method_in
        except ValueError as e:
            print(f"[ERROR] Invalid input format: {e}. Using defaults.")

    print(f"\n=======================================================")
    print(f" Starting Daily Comparison for: {args.date}")
    print(f" Grid Resolution : {args.res_lat}° Lat x {args.res_lon}° Lon ({args.method})")
    print(f" Bounding Box    : {args.bbox}")
    print(f"=======================================================")

    rebinner = SpatialRebinner(
        bbox=args.bbox,
        res_lat=args.res_lat,
        res_lon=args.res_lon,
        method=args.method
    )

    grasp_files = find_files_for_date(SYNERGY_DIR, args.date)
    s5p_files = find_files_for_date(S5P_PAL_DIR, args.date)

    if grasp_files and s5p_files:
        print(f"Found {len(grasp_files)} GRASP files and {len(s5p_files)} S5P PAL files.")
        g_lats, g_lons, g_vals = load_daily_swaths(grasp_files, GRASP_CONFIG, is_s5p=False)
        s_lats, s_lons, s_vals = load_daily_swaths(s5p_files, S5P_CONFIG, is_s5p=True)
    else:
        print(f"[NOTE] Raw NetCDF files for {args.date} not found in local directories.")
        (g_lats, g_lons, g_vals), (s_lats, s_lons, s_vals) = generate_synthetic_demo_data(args.bbox)

    print("Rebinning swaths onto common regular grid...")
    g_res = rebinner.rebin_swath(g_lats, g_lons, g_vals)
    s_res = rebinner.rebin_swath(s_lats, s_lons, s_vals)

    save_collocated_netcdf(rebinner, args.date, g_res, s_res)
    stats = compute_and_save_stats(args.date, g_res[0], s_res[0], rebinner)
    generate_quicklook(args.date, rebinner, g_res[0], s_res[0], stats)
    print("\nPipeline execution finished successfully!")


if __name__ == "__main__":
    main()