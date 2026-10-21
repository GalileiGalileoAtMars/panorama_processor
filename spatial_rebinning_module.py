"""
Spatial Rebinning Module.
Regrids irregular Level-2 satellite swath pixels onto a regular user-defined Lat/Lon grid.
"""

import numpy as np
import xarray as xr
from scipy.stats import binned_statistic_2d


class SpatialRebinner:
    def __init__(self, bbox: list, res_lat: float, res_lon: float, method: str = "mean"):
        """
        Initialize the regular spatial grid based on user inputs.
        
        :param bbox: [min_lon, min_lat, max_lon, max_lat]
        :param res_lat: Latitude grid resolution in degrees
        :param res_lon: Longitude grid resolution in degrees
        :param method: Aggregation statistic ('mean', 'median', 'std', 'count')
        """
        self.min_lon, self.min_lat, self.max_lon, self.max_lat = bbox
        self.res_lat = float(res_lat)
        self.res_lon = float(res_lon)
        self.method = method

        # Create bin edges
        self.lon_edges = np.arange(self.min_lon, self.max_lon + self.res_lon, self.res_lon)
        self.lat_edges = np.arange(self.min_lat, self.max_lat + self.res_lat, self.res_lat)

        # Create bin centers for coordinate axes
        self.lon_centers = 0.5 * (self.lon_edges[:-1] + self.lon_edges[1:])
        self.lat_centers = 0.5 * (self.lat_edges[:-1] + self.lat_edges[1:])

    def rebin_swath(self, lats: np.ndarray, lons: np.ndarray, values: np.ndarray):
        """
        Bins 1D or 2D swath arrays onto the target 2D regular grid.
        Returns rebinned values, standard deviation, and pixel counts per cell.
        """
        lats_flat = lats.ravel()
        lons_flat = lons.ravel()
        vals_flat = values.ravel()

        # Filter out NaNs and out-of-bounds coordinates
        valid_mask = (
            np.isfinite(lats_flat) &
            np.isfinite(lons_flat) &
            np.isfinite(vals_flat) &
            (lons_flat >= self.min_lon) & (lons_flat <= self.max_lon) &
            (lats_flat >= self.min_lat) & (lats_flat <= self.max_lat)
        )

        if not np.any(valid_mask):
            shape = (len(self.lat_centers), len(self.lon_centers))
            return np.full(shape, np.nan), np.full(shape, np.nan), np.zeros(shape, dtype=int)

        lats_v = lats_flat[valid_mask]
        lons_v = lons_flat[valid_mask]
        vals_v = vals_flat[valid_mask]

        # Compute primary statistic (mean or median)
        grid_val, _, _, _ = binned_statistic_2d(
            lats_v, lons_v, vals_v,
            statistic=self.method,
            bins=[self.lat_edges, self.lon_edges]
        )

        # Compute standard deviation within each grid cell
        grid_std, _, _, _ = binned_statistic_2d(
            lats_v, lons_v, vals_v,
            statistic="std",
            bins=[self.lat_edges, self.lon_edges]
        )

        # Compute number of native pixels aggregated per grid cell
        grid_count, _, _, _ = binned_statistic_2d(
            lats_v, lons_v, vals_v,
            statistic="count",
            bins=[self.lat_edges, self.lon_edges]
        )

        return grid_val, grid_std, grid_count.astype(int)