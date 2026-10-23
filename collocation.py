from aeronet import get_aeronet_dataframe

import pandas as pd
import numpy as np
import xarray as xr

import sys
import re

WL_TOLERANCE = 10.0

GCOS_FRACTION_VARS = [
    'aerosol_optical_depth_total', 'aerosol_coarse_mode_optical_depth', 'aerosol_fine_mode_optical_depth'
]

TYPICAL_BANDS = [
    340, 367, 380, 412.5, 416, 440, 442.5, 490, 494,
    510, 560, 665, 670, 747, 753, 772, 865, 1020, 2313
]

def haversine(lat1, lon1, lat2, lon2, radius=6371000):
    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)
    dlat = lat2 - lat1
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return radius * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a)) * 1e-3
    
def filter_aeronet_data ( aeronet_df, sat_ds, sat_vars, AERONET_LATITUDE_VAR, AERONET_LONGITUDE_VAR ):
    valid_mask = ( sat_ds[ sat_vars[0] ].notnull() )
    
    latitudes = sat_ds["latitude"].squeeze()
    longitudes = sat_ds["longitude"].squeeze()
    
    for idx in range ( 1, len ( sat_vars ) ):
        valid_mask |= ( sat_ds[ sat_vars[ idx ] ].notnull() )
    
    valid_lats = latitudes.where( valid_mask )
    valid_lons = longitudes.where(valid_mask)
    
    min_lat = float(valid_lats.min().item())
    max_lat = float(valid_lats.max().item())
    min_lon = float(valid_lons.min().item())
    max_lon = float(valid_lons.max().item())
    
    aeronet_df = aeronet_df.where(
        ( aeronet_df[ AERONET_LATITUDE_VAR ] >= min_lat ) &
        ( aeronet_df[ AERONET_LATITUDE_VAR ] <= max_lat ) &
        ( aeronet_df[ AERONET_LONGITUDE_VAR ] >= min_lon ) &
        ( aeronet_df[ AERONET_LONGITUDE_VAR ] <= max_lon )
    ).dropna (how = 'all')
    
    return aeronet_df, min_lat, min_lon, max_lat, max_lon

# def process_variables (
    # satellite_ds,
    # temporal_threshold,
    # spatial_threshold,
    # aeronet_data_folder,
    # AERONET_LATITUDE_VAR,
    # AERONET_LONGITUDE_VAR,
    # AERONET_PRODUCTS,
    # AERONET_SITE_VAR,
    # VARIABLE_CORRESPONDENCE,
    # include_land_percentage = False,
    # time_coordinate = "t"
# ):
    
    # S5P_FILE_DETECTED = time_coordinate == "time"
    
    # SATELLITE_VARIABLES = list ( VARIABLE_CORRESPONDENCE.keys() )
    
    # if include_land_percentage:
        # SATELLITE_VARIABLES.append ( 'land_percentage' )
        
    # if S5P_FILE_DETECTED:
        # SATELLITE_VARIABLES.extend ( [ 'latitude', 'longitude' ] )
    
    # ds = satellite_ds.get( SATELLITE_VARIABLES )
    
    # satellite_datetime = pd.to_datetime( ds.coords[ time_coordinate ].values[0] ).to_pydatetime( warn = False )
    
    # aeronet_start_datetime = ( satellite_datetime - temporal_threshold )
    # aeronet_end_datetime = ( satellite_datetime + temporal_threshold )
    
    # aeronet_df = get_aeronet_dataframe (
        # path = aeronet_data_folder,
        # start_date = aeronet_start_datetime,
        # end_date = aeronet_end_datetime,
        # products = AERONET_PRODUCTS
    # )
    
    # aeronet_df, min_lat, min_lon, max_lat, max_lon = filter_aeronet_data ( aeronet_df, ds, SATELLITE_VARIABLES, AERONET_LATITUDE_VAR, AERONET_LONGITUDE_VAR )
    
    # # if len ( aeronet_df.index ) == 0:
        # # print ( f"{', '.join(AERONET_PRODUCTS)}: No AERONET data found in bounding box (({min_lat:.2f}, {min_lon:.2f}), ({max_lat:.2f}, {max_lon:.2f}))" )
    
    # result = {
        # "datetime": satellite_datetime.isoformat(),
        # "aeronet_bounding_box": ( (min_lat, min_lon), (max_lat, max_lon) ),
        # "aeronet_sites_in_bounding_box": [ aeronet_station for aeronet_station in aeronet_df[ AERONET_SITE_VAR ].unique() ],
        # "results": { product: [] for product in SATELLITE_VARIABLES },
    # }
    
    # for sat_product, aeronet_var in VARIABLE_CORRESPONDENCE.items():
        # # Check if we need to extract AERONET wavelength or not
        # if type ( aeronet_var ) is tuple:
            # prefix = aeronet_var[0]
            # postfix = aeronet_var[1]
            # aeronet_wls = [
                # int( column_name[ len( prefix ): -1*len(postfix) ] )
                # for column_name in list ( aeronet_df )
                # if column_name.startswith(prefix) and column_name.endswith(postfix)
            # ]
        # else:
            # aeronet_wls = None
            
        # # Iterate through AERONET stations
        # for aeronet_station in aeronet_df[ AERONET_SITE_VAR ].unique():
            # aeronet_data = aeronet_df.where ( aeronet_df [ AERONET_SITE_VAR ] == aeronet_station )
            # aeronet_lat = aeronet_data[ AERONET_LATITUDE_VAR ].mean().item()
            # aeronet_lon = aeronet_data[ AERONET_LONGITUDE_VAR ].mean().item()
            
            # # Compute Haversine distance from this specific station:
            # ds = ds.assign({
                # "distance_from_station": (
                    # ds["latitude"].squeeze("time", drop=True).dims,
                    # haversine(
                        # ds["latitude"].squeeze().values, # squeeze() needed for S5P files
                        # ds["longitude"].squeeze().values, # squeeze() needed for S5P files
                        # aeronet_lat,
                        # aeronet_lon
                    # )
                # )
            # })
            
            # if 'band' not in ds.coords:
                # ds = ds.assign_coords ( band=TYPICAL_BANDS )
                
            # to_copy = [ sat_product, "distance_from_station" ]
            # if include_land_percentage:
                # to_copy.append ( 'land_percentage' )
                
            # y_dim, x_dim = ds["distance_from_station"].dims
            # y_idx, x_idx = np.where(ds["distance_from_station"].values < spatial_threshold)
            
            # if len(y_idx) > 0:
                # # 1. Crop ds[to_copy] to the tiny bounding box around the valid pixels FIRST
                # sat_data = ds[to_copy].isel({
                    # y_dim: slice(y_idx.min(), y_idx.max() + 1),
                    # x_dim: slice(x_idx.min(), x_idx.max() + 1)
                # })
                
                # # 2. Now .where() runs on a tiny ~20x20 grid instead of 3245x450!
                # sat_data = sat_data.where(sat_data["distance_from_station"] < spatial_threshold)
                # min_distance = sat_data["distance_from_station"].min().item()
                
                # # 3. Use y_dim and x_dim so it works for both S5P ('scanline'/'ground_pixel') and ('y'/'x')
                # sat_data = sat_data.dropna(x_dim, how="all", subset=(sat_product,))
                # sat_data = sat_data.dropna(y_dim, how="all", subset=(sat_product,))
            
            # # with ds[ to_copy ].copy() as sat_data:
                # # y_dim, x_dim = ds["distance_from_station"]
                # # stacked = ds[to_copy].stack(pixel=(y_dim, x_dim))
                # # condition_1d = stacked["distance_from_station"] < spatial_threshold

                
                # # # Keep only satellite data inside the required radius
                # # sat_data = sat_data.where ( sat_data[ "distance_from_station" ] < spatial_threshold )
                # # min_distance = sat_data['distance_from_station'].min().item()
                # # sat_data = sat_data.dropna ( 'x', how = 'all', subset = (sat_product, ) )
                # # sat_data = sat_data.dropna ( 'y', how = 'all', subset = (sat_product, ) )
                
                # # sat_data = stacked.isel(pixel=condition_1d)
                
                # # Check if there still is satellite data to be processed:
                # # if sat_data[ sat_product ].count().item() == 0:
                    # # There is no data to process, so skip to the next product
                    # # print ( f"{sat_product}: No satellite data in {spatial_threshold}km around AERONET station {aeronet_station}." )
                    # # continue
                    
                # if aeronet_wls is not None:
                    # # This is a spectral product, so identify the corresponding band and wavelength
                    # for sat_value in sat_data.transpose('band', ...)[ sat_product ]:
                        # sat_band = float ( sat_value.band.item() )
                        
                        # nearest_aeronet_wl = min ( aeronet_wls, key=lambda x:abs(x-sat_band) )
                        
                        # band_result = {
                            # "satellite_band": float ( sat_value.band.item() ),
                            # "satellite_data_points": sat_value.count().item(),
                            # "aeronet_station": aeronet_station,
                            # "aeronet_latitude": aeronet_lat,
                            # "aeronet_longitude": aeronet_lon,
                            # "aeronet_data_points": aeronet_data[ AERONET_SITE_VAR ].count().item(),
                            # "aeronet_wl": None
                        # }
                        
                        # if abs ( nearest_aeronet_wl - sat_band ) > WL_TOLERANCE or sat_value.count().item() == 0 or aeronet_data[f"{prefix}{int(nearest_aeronet_wl)}{postfix}"].count().item() == 0:
                            # continue
                            
                        # # Matched satellite band with AERONET wavelength. Store mean values.
                        
                        # band_result[ "aeronet_wl" ] = nearest_aeronet_wl
                        
                        # sat_mean = sat_value.mean().item()
                        
                        # prefix = aeronet_var[0]
                        # postfix = aeronet_var[1]
                        # aeronet_mean = aeronet_data[f"{prefix}{int(nearest_aeronet_wl)}{postfix}"].mean()
                            
                        # band_result = {
                            # **band_result,
                            # "satellite_mean": sat_mean,
                            # "aeronet_mean": float ( aeronet_mean ),
                            # "satellite_data_points": sat_value.count().item(),
                            # "aeronet_data_points": aeronet_data[f"{prefix}{int(nearest_aeronet_wl)}{postfix}"].count().item()
                        # }
                        
                        # if include_land_percentage:
                            # band_result[ "land_percentage" ] = sat_data[ "land_percentage" ].mean().item()
                        
                        # result["results"][ sat_product ].append ( band_result )
                # else:
                    # satellite_count = sat_data[ sat_product ].count().item()
                    # aeronet_count = aeronet_data[ aeronet_var ].count().item()
                    
                    # if satellite_count == 0 or aeronet_count == 0:
                        # continue
                        
                    # satellite_mean = sat_data[ sat_product ].mean().item()
                    # aeronet_mean = aeronet_data[ aeronet_var ].mean().item()
                    
                    # r = {
                        # "satellite_band": None,
                        # "aeronet_station": aeronet_station,
                        # "aeronet_latitude": aeronet_lat,
                        # "aeronet_longitude": aeronet_lon,
                        # "aeronet_wl": None,
                        # "satellite_mean": satellite_mean,
                        # "aeronet_mean": aeronet_mean,
                        # "satellite_data_points": sat_data[ sat_product ].count().item(),
                        # "aeronet_data_points": aeronet_data[ aeronet_var ].count().item(),
                        # "land_percentage": sat_data[ "land_percentage" ].mean().item()
                    # }
                    
                    # if include_land_percentage:
                        # r[ "land_percentage" ] = sat_data[ "land_percentage" ].mean().item()
                        
                    # result["results"][ sat_product ].append ( r )
            
    # return result

def process_variables(
    satellite_ds,
    temporal_threshold,
    spatial_threshold,
    aeronet_data_folder,
    AERONET_LATITUDE_VAR,
    AERONET_LONGITUDE_VAR,
    AERONET_PRODUCTS,
    AERONET_SITE_VAR,
    VARIABLE_CORRESPONDENCE,
    include_land_percentage=False,
    time_coordinate="t",
):
    S5P_FILE_DETECTED = time_coordinate == "time"
    product_vars = list(VARIABLE_CORRESPONDENCE.keys())
    sat_vars_to_extract = product_vars.copy()

    if include_land_percentage:
        sat_vars_to_extract.append("land_percentage")

    if S5P_FILE_DETECTED:
        sat_vars_to_extract.extend(["latitude", "longitude"])

    ds = satellite_ds.get(sat_vars_to_extract)

    # 1. Extract timestamp safely
    sat_time_val = np.atleast_1d(ds.coords[time_coordinate].values)[0]
    satellite_datetime = pd.to_datetime(sat_time_val).to_pydatetime()

    aeronet_df = get_aeronet_dataframe(
        path=aeronet_data_folder,
        start_date=satellite_datetime - temporal_threshold,
        end_date=satellite_datetime + temporal_threshold,
        products=AERONET_PRODUCTS,
    )
    
    if aeronet_df is None or aeronet_df.empty:
        return {
            "datetime": satellite_datetime.isoformat(),
            "aeronet_bounding_box": None,
            "aeronet_sites_in_bounding_box": [],
            "results": {product: [] for product in product_vars},
        }

    aeronet_df, min_lat, min_lon, max_lat, max_lon = filter_aeronet_data(
        aeronet_df, ds, product_vars, AERONET_LATITUDE_VAR, AERONET_LONGITUDE_VAR
    )

    unique_stations = aeronet_df[AERONET_SITE_VAR].dropna().unique().tolist()

    result = {
        "datetime": satellite_datetime.isoformat(),
        "aeronet_bounding_box": ((min_lat, min_lon), (max_lat, max_lon)),
        "aeronet_sites_in_bounding_box": unique_stations,
        "results": {product: [] for product in product_vars},
    }

    if not unique_stations:
        return result

    # 2. Detect spectral dimension ('wavelength' for S5P, 'band' for standard files)
    spectral_dim = "wavelength" if "wavelength" in ds.dims else "band"
    if spectral_dim not in ds.coords and spectral_dim in ds.dims:
        ds = ds.assign_coords({spectral_dim: TYPICAL_BANDS})

    # 3. Pre-extract 2D lat/lon once (works for both S5P and standard files)
    lat_2d = ds["latitude"].squeeze(drop=True)
    lon_2d = ds["longitude"].squeeze(drop=True)
    y_dim, x_dim = lat_2d.dims

    # 4. Pre-compute AERONET wavelengths for each product once
    product_wls = {}
    for sat_product, aeronet_var in VARIABLE_CORRESPONDENCE.items():
        if isinstance(aeronet_var, tuple):
            prefix, postfix = aeronet_var
            product_wls[sat_product] = [
                int(col[len(prefix) : len(col) - len(postfix)])
                for col in aeronet_df.columns
                if col.startswith(prefix) and col.endswith(postfix)
            ]
        else:
            product_wls[sat_product] = None

    # 5. Loop over STATIONS first so Haversine & spatial indexing run only ONCE per station
    for aeronet_station, aeronet_data in aeronet_df.groupby(AERONET_SITE_VAR):
        aeronet_lat = float(aeronet_data[AERONET_LATITUDE_VAR].mean())
        aeronet_lon = float(aeronet_data[AERONET_LONGITUDE_VAR].mean())

        # Compute 2D distance array (pure NumPy)
        dist_2d = haversine(lat_2d.values, lon_2d.values, aeronet_lat, aeronet_lon)
        y_idx, x_idx = np.where(dist_2d < spatial_threshold)

        # Skip station immediately if no satellite pixels fall within radius
        if len(y_idx) == 0:
            continue

        min_distance = float(dist_2d[y_idx, x_idx].min())

        # Extract ONLY valid pixels into a 1D 'pixel' dimension (no 2D NaN grid needed!)
        station_ds = ds.isel({
            y_dim: xr.DataArray(y_idx, dims="pixel"),
            x_dim: xr.DataArray(x_idx, dims="pixel"),
        })

        # 6. Now loop over each satellite product for this station
        for sat_product, aeronet_var in VARIABLE_CORRESPONDENCE.items():
            sat_da = station_ds[sat_product]

            # Valid pixel mask for this product (for matching land_percentage)
            if include_land_percentage:
                land_da = station_ds["land_percentage"]

            aeronet_wls = product_wls[sat_product]

            if aeronet_wls is not None:
                # Spectral product: iterate over bands/wavelengths
                for sat_band_val in sat_da[spectral_dim]:
                    sat_band = float(sat_band_val.item())
                    sat_slice = sat_da.sel({spectral_dim: sat_band_val})
                    sat_count = int(sat_slice.count().item())

                    if sat_count == 0 or not aeronet_wls:
                        continue

                    nearest_wl = min(aeronet_wls, key=lambda w: abs(w - sat_band))
                    if abs(nearest_wl - sat_band) > WL_TOLERANCE:
                        continue

                    prefix, postfix = aeronet_var
                    aeronet_col = f"{prefix}{int(nearest_wl)}{postfix}"
                    aeronet_count = int(aeronet_data[aeronet_col].count())

                    if aeronet_count == 0:
                        continue

                    band_result = {
                        "satellite_band": sat_band,
                        "aeronet_station": aeronet_station,
                        "aeronet_latitude": aeronet_lat,
                        "aeronet_longitude": aeronet_lon,
                        "aeronet_wl": nearest_wl,
                        "satellite_mean": float(sat_slice.mean().item()),
                        "aeronet_mean": float(aeronet_data[aeronet_col].mean()),
                        "satellite_data_points": sat_count,
                        "aeronet_data_points": aeronet_count,
                        "min_distance": min_distance,
                    }

                    if include_land_percentage:
                        # Average land_percentage only over pixels where sat_slice is not NaN
                        valid_land = land_da.where(sat_slice.notnull())
                        band_result["land_percentage"] = float(valid_land.mean().item())

                    result["results"][sat_product].append(band_result)

            else:
                # Non-spectral product
                sat_count = int(sat_da.count().item())
                aeronet_count = int(aeronet_data[aeronet_var].count())

                if sat_count == 0 or aeronet_count == 0:
                    continue

                r = {
                    "satellite_band": None,
                    "aeronet_station": aeronet_station,
                    "aeronet_latitude": aeronet_lat,
                    "aeronet_longitude": aeronet_lon,
                    "aeronet_wl": None,
                    "satellite_mean": float(sat_da.mean().item()),
                    "aeronet_mean": float(aeronet_data[aeronet_var].mean()),
                    "satellite_data_points": sat_count,
                    "aeronet_data_points": aeronet_count,
                    "min_distance": min_distance,
                }

                if include_land_percentage:
                    valid_land = land_da.where(sat_da.notnull())
                    r["land_percentage"] = float(valid_land.mean().item())

                result["results"][sat_product].append(r)

    return result