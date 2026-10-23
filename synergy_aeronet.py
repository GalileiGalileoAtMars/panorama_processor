SCRIPT_NAME = "panorama-collocation"
SCRIPT_VERSION = "0.1.0"
SCRIPT_DESCRIPTION = "Collocate satellite and ground data."

# SATELLITE_FILE_REGEX_v002 = r'^GRASP_SYN_OLCIA\+OLCIB\+TROPOMI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__(OLCI_A|OLCI_B|TROPOMI)_[0-9]+_002*.nc$'
# SATELLITE_FILE_REGEX_v003 = r'^GRASP_SYN_OLCI\+TROPOMI\+AHI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__(OLCI|Tropomi|AHI)_[0-9]+_003*.nc$'
SATELLITE_FILE_REGEX = r'^GRASP_SYN_OLCI\+TROPOMI\+AHI__(\d{4}\d{2}\d{2}T\d{2}\d{2}\d{2})__(OLCI|Tropomi|AHI)_003.nc$'
# GRASP_SYN_OLCIA+OLCIB+TROPOMI__20250615T071355__OLCI_B_0000334_002.nc

import argparse
import sys

import concurrent.futures
import itertools

import os
import pandas as pd
from pathlib import Path
import re
import xarray as xr
from datetime import date, timedelta, datetime
import json

from alive_progress import alive_it

from aeronet import download_aeronet_data, get_aeronet_dataframe, read_aeronet_stations_file
from collocation import process_variables, WL_TOLERANCE

def find_satellite_files ( folder_path : str | Path ):
    data_path = Path ( os.path.abspath ( folder_path ) )
    sat_files = []
    
    for root, dirs, files in os.walk ( data_path ):
        for filename in files:
            # print (f"Testing {filename=} against {SATELLITE_FILE_REGEX=}")
            match = re.search ( SATELLITE_FILE_REGEX, filename )
            
            if match:
                sat_files.append ( Path ( os.path.join ( root, filename ) ) )
            else:
                print ( f"File {filename} does not match SATELLITE_FILE_REGEX: {SATELLITE_FILE_REGEX}" )
                
    return sat_files
    
def download_aeronet_files ( satellite_files, aeronet_data_folder, temporal_threshold, redownload = False ):
    measurement_dates = []
    
    for sat_file in satellite_files:
        match = re.search ( SATELLITE_FILE_REGEX, os.path.basename ( sat_file ) )
        
        date_str = match.group(1)
        
        if not date_str:
           continue
           
        satellite_datetime = datetime.strptime(date_str, "%Y%m%dT%H%M%S")
        
        start_date = ( satellite_datetime - temporal_threshold ).date()
        end_date = ( satellite_datetime + temporal_threshold ).date()
        
        if start_date not in measurement_dates:
            measurement_dates.append ( start_date )
            
        if end_date not in measurement_dates:
            measurement_dates.append ( end_date )
    
    for date in measurement_dates:
        files = download_aeronet_data (
            path = aeronet_data_folder,
            start_date = date,
            end_date = date,
            products = [ "SSA", "AOD", "TAB" ],
            # site = aeronet_station['name'],
            site = None,
            avg_type = 10, # all data points
            redownload = redownload
        )
        
def process_satellite_file ( satellite_file, temporal_threshold, spatial_threshold, aeronet_stations, aeronet_data_folder ):
    # print ("===========================================================================")
    # print (f"Processing satellite file {os.path.basename(satellite_file)}")
    # print ("===========================================================================")
    
    with xr.open_dataset ( satellite_file ) as ds:
        aod_result = process_variables (
            ds, temporal_threshold,
            spatial_threshold,
            aeronet_data_folder,
            AERONET_LATITUDE_VAR = "Latitude(Degrees)",
            AERONET_LONGITUDE_VAR = "Longitude(Degrees)",
            AERONET_PRODUCTS = [ "AOD" ],
            AERONET_SITE_VAR = "AERONET_Site",
            VARIABLE_CORRESPONDENCE = {
                'aerosol_optical_depth_total': ("AOD_Extinction-Total[", "nm]"),
                'aerosol_coarse_mode_optical_depth': ("AOD_Extinction-Coarse[", "nm]"),
                'aerosol_fine_mode_optical_depth': ("AOD_Extinction-Fine[", "nm]"),
                'aerosol_angstrom_exponent': "Extinction_Angstrom_Exponent_440-870nm-Total"
            },
            include_land_percentage = True
        )
        
        ssa_result = process_variables (
            ds, temporal_threshold,
            spatial_threshold,
            aeronet_data_folder,
            AERONET_LATITUDE_VAR = "Latitude(Degrees)",
            AERONET_LONGITUDE_VAR = "Longitude(Degrees)",
            AERONET_PRODUCTS = [ "SSA" ],
            AERONET_SITE_VAR = "AERONET_Site",
            VARIABLE_CORRESPONDENCE = {
                'aerosol_single_scattering_albedo_total': ("Single_Scattering_Albedo[", "nm]")
            },
            include_land_percentage = True
        )
        
        tab_result = process_variables (
            ds, temporal_threshold,
            spatial_threshold,
            aeronet_data_folder,
            AERONET_LATITUDE_VAR = "Latitude(Degrees)",
            AERONET_LONGITUDE_VAR = "Longitude(Degrees)",
            AERONET_PRODUCTS = [ "TAB" ],
            AERONET_SITE_VAR = "AERONET_Site",
            VARIABLE_CORRESPONDENCE = {
                'aerosol_absorption_optical_depth_total': ("Absorption_AOD[", "nm]")
            },
            include_land_percentage = True
        )
                    
        return aod_result, ssa_result, tab_result

def process_satellite_files ( satellite_files, temporal_threshold, spatial_threshold, aeronet_stations, aeronet_data_folder, json_output ):
    idx = 0
    results = {
        "aod": [],
        "ssa": [],
        "tab": []
    }
                
    with concurrent.futures.ProcessPoolExecutor() as executor:
        args = (
            satellite_files,
            itertools.repeat(temporal_threshold),
            itertools.repeat(spatial_threshold),
            itertools.repeat(aeronet_stations),
            itertools.repeat(aeronet_data_folder),
        )
        
        processing_results = list(
            alive_it(
                executor.map(process_satellite_file, *args),
                total=len(satellite_files),
                dual_line=True,
                enrich_print=False,
            )
        )

        for processing_result in processing_results:
            if processing_result[0] is not None:
                results["aod"].append ( processing_result[0] )
                
            if processing_result[1] is not None:
                results["ssa"].append ( processing_result[1] )
                
            if processing_result[2] is not None:
                results["tab"].append ( processing_result[2] )
            
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
        description="Collocate satellite and ground data.",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"{SCRIPT_NAME} {SCRIPT_VERSION}",
    )
    
    parser.add_argument("--satellite-folder", required=True, dest="satellite_data_folder")
    parser.add_argument("--aeronet-folder", required=True, dest="aeronet_data_folder")
    parser.add_argument("--aeronet-stations-csv", required=True, dest="aeronet_stations_csv")
    parser.add_argument("--spatial-threshold", required=True, dest="spatial_threshold", help="Radius in kilometers in which to collocate data.", type=int)
    parser.add_argument("--temporal-threshold", required=True, dest="temporal_threshold", help="Time period in minutes in which to collocate data.", type=int)
    
    parser.add_argument("--download-aeronet", action="store_true", default=False, dest="download_aeronet", help="Whether to download AERONET data.")
    parser.add_argument("--redownload-aeronet", action="store_true", default=False, dest="redownload", help="Whether to redownload AERONET data in case the files already exists.")
    
    parser.add_argument("json_output", metavar="json-output", help="Destination JSON file containing the processing results.")
            
    return parser.parse_args()
    
if __name__ == "__main__":
    args = parse_args ()
    
    print ( "Processing started with the following parameters:" )
    print ( f"\tSatellite data folder: {args.satellite_data_folder}" )
    print ( f"\tAERONET data folder: {args.aeronet_data_folder}" )
    print ( f"\tAERONET stations CSV file: {os.path.abspath ( args.aeronet_stations_csv )}" )
    print ( f"\tSpatial threshold: {args.spatial_threshold} km" )
    print ( f"\tTemporal threshold: {args.temporal_threshold} minutes" )
    print ( f"\tAERONET data redownloading: {args.redownload}" )
    print ( f"\tJSON output file: {args.json_output}" )
    print ( "" )
    
    aeronet_stations = read_aeronet_stations_file ( args.aeronet_stations_csv )
    
    satellite_files = find_satellite_files ( args.satellite_data_folder )
    print (f"Found {len(satellite_files)} satellite files in {args.satellite_data_folder}")
    print (f"Found {len(aeronet_stations)} AERONET stations in {args.aeronet_stations_csv}")
    
    if args.download_aeronet:
        download_aeronet_files (
            satellite_files, args.aeronet_data_folder,
            temporal_threshold = timedelta ( minutes = args.temporal_threshold ),
            redownload = args.redownload
        )
    
    process_satellite_files (
        satellite_files,
        temporal_threshold = timedelta ( minutes = args.temporal_threshold ),
        spatial_threshold = args.spatial_threshold,
        aeronet_stations = aeronet_stations,
        aeronet_data_folder = args.aeronet_data_folder,
        json_output = args.json_output
    )
    
    sys.exit (0)