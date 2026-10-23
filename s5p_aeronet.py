SCRIPT_NAME = "panorama-s5p"
SCRIPT_VERSION = "0.1.0"
SCRIPT_DESCRIPTION = "Collocate S5P data with AERONET ground-based measurements."

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import re
import sys
import pickle
import json
import os

import concurrent.futures
import itertools
from alive_progress import alive_it

import xarray as xr
import netCDF4

from aeronet import download_aeronet_data, get_aeronet_dataframe, read_aeronet_stations_file, download_aeronet_files
from collocation import process_variables, WL_TOLERANCE

S5P_PATTERN = re.compile ( r"^S5P_PAL__L2__AER_OT_(\d{8})T(\d{6})_(\d{8})T(\d{6})_(\d{5})_(\d{2})_(\d{6})_(\d{8})T(\d{6}).nc$" )

SYN_AOT_VAR = "aerosol_optical_depth_total"
S5P_AOT_VAR = "aerosol_optical_thickness"

SYNERGY_PATTERNS = [
    # r"^GRASP_SYN_OLCIA\+OLCIB\+TROPOMI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__(OLCI|TROPOMI)_XXXXXXX_001*.nc$",
    r"^GRASP_SYN_OLCIA\+OLCIB\+TROPOMI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__TROPOMI_XXXXXXX_001*.nc$",
    # r"^GRASP_SYN_OLCIA\+OLCIB\+TROPOMI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__(OLCI_A|OLCI_B|TROPOMI)_[0-9]+_002*.nc$",
    r"^GRASP_SYN_OLCIA\+OLCIB\+TROPOMI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__TROPOMI_([0-9]+)_002*.nc$",
    # r"^GRASP_SYN_OLCI\+TROPOMI\+AHI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__(OLCI|Tropomi|AHI)_003.nc$",
    r"^GRASP_SYN_OLCI\+TROPOMI\+AHI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__Tropomi_003.nc$",
]

SYN_TYPICAL_BANDS = [
    340, 367, 380, 412.5, 416, 440, 442.5, 490, 494,
    510, 560, 665, 670, 747, 753, 772, 865, 1020, 2313
]

def boxes_intersect(box1, box2):
    """
    Checks if two lat-lon bounding boxes intersect.
    Each box is defined as ((min_lat, min_lon), (max_lat, max_lon)).
    """
    (lat_min1, lon_min1), (lat_max1, lon_max1) = box1
    (lat_min2, lon_min2), (lat_max2, lon_max2) = box2

    # Check for overlap on both latitude and longitude axes
    lat_overlap = (lat_min1 <= lat_max2) and (lat_min2 <= lat_max1)
    lon_overlap = (lon_min1 <= lon_max2) and (lon_min2 <= lon_max1)

    return lat_overlap and lon_overlap
    
def join_boxes (box1, box2):
    (lat_min1, lon_min1), (lat_max1, lon_max1) = box1
    (lat_min2, lon_min2), (lat_max2, lon_max2) = box2
    
    return ( min ( lat_min1, lat_min2 ), max ( lat_max1, lat_max2 ) ), ( min ( lon_min1, lon_min2 ), max ( lon_max1, lon_max2 ) )

def process_s5p_file ( s5p_file_path, synergy_file_path, synergy_bounds ):
    with xr.open_dataset ( s5p_file_path, group="/PRODUCT" ) as ds:
        valid_mask = ds[ S5P_AOT_VAR ].notnull()
        
        valid_lats = ds["latitude"].where( valid_mask )
        valid_lons = ds["longitude"].where( valid_mask )
        
        lat_min = float(valid_lats.min().item())
        lat_max = float(valid_lats.max().item())
        lon_min = float(valid_lons.min().item())
        lon_max = float(valid_lons.max().item())
        
        s5p_bounds = ( (lat_min, lat_max), (lon_min, lon_max) )
        
        if not boxes_intersect ( synergy_bounds, s5p_bounds ):
            print ( "File {os.path.basename(s5p_file_path)} does not intersect typical SYNERGY polygon. Skipping..." )
            
def extract_synergy_file_data ( synergy_file, synergy_filename_patterns = SYNERGY_PATTERNS ):
    # Read lat-lon bounds for each band separately (maybe they differ, who knows?)
    bounds = {}

    with xr.open_dataset ( synergy_file ) as ds:
        if 'band' not in ds.coords:
            ds = ds.assign_coords ( band=SYN_TYPICAL_BANDS )

        # for syn_value in ds.transpose('band', ...)[ SYN_AOT_VAR ]:
            # syn_band = float ( syn_value.band.item() )
        valid_mask = ds[ SYN_AOT_VAR ].notnull()

        valid_lats = ds["latitude"].where( valid_mask )
        valid_lons = ds["longitude"].where( valid_mask )

        lat_min = float(valid_lats.min().item())
        lat_max = float(valid_lats.max().item())
        lon_min = float(valid_lons.min().item())
        lon_max = float(valid_lons.max().item())

        bounds = ( ( lat_min, lon_min), (lat_max, lon_max) )
        
        return {
            "bounds": bounds
        }
            
def index_synergy_files ( synergy_folder, synergy_filename_patterns = SYNERGY_PATTERNS ):
    # Index SYNERGY files
    synergy_records = []
    bounds = None
    for file_path in synergy_folder.rglob("*.nc"):
        filename = file_path.name
        for pattern in synergy_filename_patterns:
            match = re.match(pattern, filename)
            if match:
                print (f"Reading metadata from {filename} ...")
                
                time_str = match.group(1)

                data = extract_synergy_file_data ( file_path )
                syn_bounds = data["bounds"]
                
                # for syn_bounds in data["bounds"]:
                if bounds is None:
                    bounds = syn_bounds
                else:
                    bounds = join_boxes ( syn_bounds, bounds )
                
                synergy_records.append({
                **data,
                  "path": file_path,
                  "filename": filename,
                  "timestamp": datetime.strptime(time_str, "%Y%m%dT%H%M%S")
                })
        
        # if bounds is not None:
            # # Stop after first valid file. Used for testing.
            # break
                
    return synergy_records, bounds
    
def extract_synergy_dates ( records ):
    if records is None or len(records) < 1:
        return None, None
        
    day_dict = {}
        
    for record in records:
        day = record["timestamp"].date()
        bounds = record["bounds"]
        
        if day in day_dict:
            bounds = join_boxes ( day_dict[ day ], bounds )
            
        day_dict[ day ] = bounds
        
    return day_dict
        
    # return list ( { day_dict.keys() } ), list ( day_dict.values() )
        
        
    # return sorted ( list ( { r["timestamp"].date() for r in records } ) )
    
def identify_s5p_files ( root_dir, dates ):
    matching_files = {}
    
    if type(dates) is dict:
        for d, bounds in dates.items():
            target_dir = target_dir = root_dir / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}"
            
            if target_dir.is_dir():
                # for file in target_dir.rglob('*'):
                    # path = file.resolve()
                    # if file.is_file and S5P_PATTERN.search ( file.name ):
                        # matching_files[ path ] = bounds
                        
                matching_files.update ({
                    str ( file.resolve() ): bounds for file in target_dir.rglob('*')
                    if file.is_file and S5P_PATTERN.search ( file.name )
                })
    else:
        # Fallback to return every S5P file available in the root_dir and its subfolders
        print ( "No synergy records could be read so no filtering of available S5P files is performed. Try to use --dump-synergy-records or --load-synergy-records" )
        
        matching_files = {
            str( file.resolve() ): None for file in root_dir.rglob('*')
            if file.is_file() and S5P_PATTERN.search ( file.name )
        }
        
    return matching_files
    
def process_satellite_file ( satellite_file, synergy_bounds, temporal_threshold, spatial_threshold, aeronet_stations, aeronet_data_folder ):
    # print ("===========================================================================")
    # print (f"Processing satellite file {os.path.basename(satellite_file)}")
    # print ("===========================================================================")
    
    with xr.open_dataset ( satellite_file, group="/PRODUCT" ) as ds:
        valid_mask = ds[ S5P_AOT_VAR ].notnull()

        valid_lats = ds["latitude"].where( valid_mask )
        valid_lons = ds["longitude"].where( valid_mask )

        lat_min = float(valid_lats.min().item())
        lat_max = float(valid_lats.max().item())
        lon_min = float(valid_lons.min().item())
        lon_max = float(valid_lons.max().item())
        
        if not boxes_intersect ( synergy_bounds, ( (lat_min, lon_min), (lat_max, lon_max) ) ):
            # print (f"Skipping file {os.path.basename(satellite_file)} because it doesn't intersect synergy product in area {synergy_bounds}.")
            return None
        
        aod_result = process_variables (
            ds, temporal_threshold,
            spatial_threshold,
            aeronet_data_folder,
            AERONET_LATITUDE_VAR = "Latitude(Degrees)",
            AERONET_LONGITUDE_VAR = "Longitude(Degrees)",
            AERONET_PRODUCTS = [ "AOD" ],
            AERONET_SITE_VAR = "AERONET_Site",
            VARIABLE_CORRESPONDENCE = {
                S5P_AOT_VAR: ("AOD_Extinction-Total[", "nm]")
            },
            time_coordinate = "time"
        )
                    
    return aod_result
        
def process_satellite_files ( satellite_files, synergy_bounds, temporal_threshold, spatial_threshold, aeronet_stations, aeronet_data_folder, json_output ):
    results = {
        "aod": []
    }
    
    file_paths = list ( satellite_files.keys() )
    file_bounds = list ( satellite_files.values() )
                
    with concurrent.futures.ProcessPoolExecutor() as executor:
        args = (
            file_paths,
            file_bounds,
            itertools.repeat(temporal_threshold),
            itertools.repeat(spatial_threshold),
            itertools.repeat(aeronet_stations),
            itertools.repeat(aeronet_data_folder),
        )
        
        processing_results = list(
            alive_it(
                executor.map(process_satellite_file, *args),
                total=len(file_paths),
                dual_line=True,
                enrich_print=False,
            )
        )

        for processing_result in processing_results:
            if processing_result is not None:
                results["aod"].append ( processing_result )
            
    result_file_path = os.path.abspath ( json_output )
    result_folder = os.path.dirname ( result_file_path )
    
    if not os.path.exists ( result_folder ):
        os.makedirs ( result_folder )
        
    results.update({
        "temporal_threshold_minutes": temporal_threshold.seconds / 60,
        "spatial_threshold_km": spatial_threshold,
        "wavelength_threshold_nm": WL_TOLERANCE,
    })
        
    with open ( result_file_path, 'w' ) as file:
        json.dump ( results, file )
    
def parse_args ():
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description=SCRIPT_DESCRIPTION
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SCRIPT_NAME} {SCRIPT_VERSION}",
    )
    
    parser.add_argument("--synergy-folder", "-y", required=True, dest="synergy_folder")
    parser.add_argument("--dump-synergy-records", "-d", dest="dump_synergy_records", type=str)
    parser.add_argument("--load-synergy-records", "-l", dest="load_synergy_records", type=str)
    
    parser.add_argument("--s5p-folder", required=True, dest="s5p_folder", help="Location of the S5P data files.")
    
    parser.add_argument("--aeronet-folder", required=True, dest="aeronet_data_folder")
    parser.add_argument("--aeronet-stations-csv", required=True, dest="aeronet_stations_csv")
    
    parser.add_argument("--spatial-threshold", required=True, dest="spatial_threshold", help="Radius in kilometers in which to collocate data.", type=int)
    parser.add_argument("--temporal-threshold", required=True, dest="temporal_threshold", help="Time period in minutes in which to collocate data.", type=int)
    parser.add_argument("--download-aeronet", action="store_true", default=False, dest="download_aeronet", help="Whether to download AERONET data.")
    parser.add_argument("--redownload-aeronet", action="store_true", default=False, dest="redownload_aeronet", help="Whether to redownload AERONET data in case the files already exists.")
    
    parser.add_argument("json_output", metavar="json-output", help="Destination JSON file containing the processing results.")
    
    return parser.parse_args()
    
if __name__ == "__main__":
    args = parse_args ()
    
    print ( "Processing started with the following parameters:" )
    print ( f"\tSynergy data folder: {os.path.abspath ( args.synergy_folder )}" )
    print ( f"\tDump synergy records: {args.dump_synergy_records}" )
    print ( f"\tLoad synergy records: {args.load_synergy_records}" )
    print ( f"\tAERONET data folder: {os.path.abspath ( args.aeronet_data_folder )}" )
    print ( f"\tAERONET stations CSV file: {os.path.abspath ( args.aeronet_stations_csv )}" )
    print ( f"\tSpatial threshold: {args.spatial_threshold} km" )
    print ( f"\tTemporal threshold: {args.temporal_threshold} minutes" )
    print ( f"\tAERONET data redownloading: {args.redownload_aeronet}" )
    print ( f"\tJSON output file: {args.json_output}" )
    print ( f"\tS5P data folder: {args.s5p_folder}" )
    print ( "" )
    
    results = None
    synergy_bounds = None
    
    if args.dump_synergy_records:
        synergy_records, synergy_bounds = index_synergy_files ( Path ( args.synergy_folder ) )
        
        results = {
            "records": synergy_records,
            "bounds": synergy_bounds
        }
        
        print ( f"Found {len(synergy_records)} synergy data files. All data is located inside {results['bounds']} polygon." )
        
        with open( args.dump_synergy_records, 'wb' ) as file:
            # json.dump ( results, file )
            pickle.dump ( results, file )
            
        print ( f"Results saved in {os.path.abspath ( args.dump_synergy_records )}." )
        
        sys.exit (0)
        
    elif args.load_synergy_records:
        with open ( args.load_synergy_records, 'rb' ) as file:
            results = pickle.load ( file )
            
    # if results is None:
        # print ("Synergy records not read. Please use --dump-synergy-records or --load-synergy-records! Exiting.")
        # sys.exit (-1)
        
        
    days = extract_synergy_dates ( results["records"] ) if results is not None else None
    
    # for day, bound in days.items():
        # print ( f"{day}: Data between ({bound[0][0]:.2f}, {bound[0][1]:.2f}), ({bound[1][0]:.2f}, {bound[1][1]:.2f})" )
        
    # sys.exit (0)
    
    if type(synergy_bounds) is not tuple:
        synergy_bounds = results["bounds"] if results is not None else None
    
    if args.download_aeronet:
        if days is not None:
            download_aeronet_files (
                list ( days.keys() ), args.aeronet_data_folder,
                temporal_threshold = timedelta ( minutes = args.temporal_threshold ),
                redownload = args.redownload_aeronet
            )
        else:
            print ('Skipping AERONET data downloading because no synergy records could be read to extract measurement dates.')
        
    aeronet_stations = read_aeronet_stations_file ( args.aeronet_stations_csv )
    
    if args.s5p_folder is not None:
        candidate_s5p_files = identify_s5p_files ( Path ( args.s5p_folder ), days )
        
        print ( f"Found {len(candidate_s5p_files)} candidate S5P files in {str ( Path ( args.s5p_folder ).resolve() )}" )
        
        process_satellite_files (
            candidate_s5p_files,
            synergy_bounds,
            temporal_threshold = timedelta ( minutes = args.temporal_threshold ),
            spatial_threshold = args.spatial_threshold,
            aeronet_stations = aeronet_stations,
            aeronet_data_folder = args.aeronet_data_folder,
            json_output = args.json_output
        )

    sys.exit (0)