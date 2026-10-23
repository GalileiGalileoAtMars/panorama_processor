AERONET_CSV_COLUMNS_NA_VALUES = {
    "AOD_1640nm": -999.0,
    "AOD_1020nm": -999.0,
    "AOD_870nm": -999.0,
    "AOD_865nm": -999.0,
    "AOD_779nm": -999.0,
    "AOD_675nm": -999.0,
    "AOD_667nm": -999.0,
    "AOD_620nm": -999.0,
    "AOD_560nm": -999.0,
    "AOD_555nm": -999.0,
    "AOD_551nm": -999.0,
    "AOD_532nm": -999.0,
    "AOD_531nm": -999.0,
    "AOD_510nm": -999.0,
    "AOD_500nm": -999.0,
    "AOD_490nm": -999.0,
    "AOD_443nm": -999.0,
    "AOD_440nm": -999.0,
    "AOD_412nm": -999.0,
    "AOD_400nm": -999.0,
    "AOD_380nm": -999.0,
    "AOD_340nm": -999.0,
    "1640nm_Input_AOD": -999.0,
    "1020nm_Input_AOD": -999.0,
    "870nm_Input_AOD": -999.0,
    "865nm_Input_AOD": -999.0,
    "779nm_Input_AOD": -999.0,
    "675nm_Input_AOD": -999.0,
    "667nm_Input_AOD": -999.0,
    "620nm_Input_AOD": -999.0,
    "560nm_Input_AOD": -999.0,
    "555nm_Input_AOD": -999.0,
    "551nm_Input_AOD": -999.0,
    "532nm_Input_AOD": -999.0,
    "531nm_Input_AOD": -999.0,
    "510nm_Input_AOD": -999.0,
    "500nm_Input_AOD": -999.0,
    "490nm_Input_AOD": -999.0,
    "443nm_Input_AOD": -999.0,
    "440nm_Input_AOD": -999.0,
    "412nm_Input_AOD": -999.0,
    "400nm_Input_AOD": -999.0,
    "380nm_Input_AOD": -999.0,
    "340nm_Input_AOD": -999.0,
    "440-870_Angstrom_Exponent": -999.0,
    "380-500_Angstrom_Exponent": -999.0,
    "440-675_Angstrom_Exponent": -999.0,
    "500-870_Angstrom_Exponent": -999.0,
    "340-440_Angstrom_Exponent": -999.0,
    "Total_AOD_500nm[tau_a]": -999.0,
    "Fine_Mode_AOD_500nm[tau_f]": -999.0,
    "Coarse_Mode_AOD_500nm[tau_c]": -999.0,
    "FineModeFraction_500nm[eta]": -999.0,
    "Angstrom_Exponent(AE)-Total_500nm[alpha]": -999.0,
    "Single_Scattering_Albedo[440nm]": -999.0,
    "Single_Scattering_Albedo[675nm]": -999.0,
    "Single_Scattering_Albedo[870nm]": -999.0,
    "Single_Scattering_Albedo[1020nm]": -999.0
}

CSV_COLUMNS = list ( AERONET_CSV_COLUMNS_NA_VALUES.keys() )
CSV_COLUMNS.extend ( ['AERONET_Site', 'Date(dd:mm:yyyy)', 'Time(hh:mm:ss)', 'Site_Latitude(Degrees)', 'Site_Longitude(Degrees)'] )

INVERSION_PRODUCTS = [ "SSA", "AOD", "TAB" ]

import io
from datetime import date, datetime, timedelta
import requests
import pandas as pd
from pathlib import Path
import os

def daterange (start_date: date, end_date: date):
    days = int ( ( end_date - start_date ).days )
    
    for n in range ( days + 1 ):
        yield start_date + timedelta(n)
        
def aeronet_file_path ( base_folder: str | Path, measurement_date: date, product: str, structured: bool = True ):
    folder = base_folder
    filename = f"{measurement_date.strftime('%Y-%m-%d')}_{product}.csv"
    
    if structured:
        folder = os.path.join ( folder, f"{measurement_date.strftime('%Y')}", f"{measurement_date.strftime('%m')}" )
        
    return os.path.join ( folder, filename )

def fetch_aeronet_data(
    start_date: date,
    end_date: date,
    products: list[str] = [ "AOD15" ],
    site: str = None,
    avg_type: int = 10,
    if_no_html: int = 1
) -> dict[str: str]:
    """
    Queries the NASA AERONET V3 API for aerosol data.
    
    Parameters:
    -----------
    start_date : str
        Start date formatted as 'YYYY-MM-DD'.
    end_date : str
        End date formatted as 'YYYY-MM-DD'.
    product : str
        Data product type. Common options:
          - 'AOD10', 'AOD15', 'AOD20' (Level 1.0, 1.5, 2.0 Aerosol Optical Depth)
          - 'SDA10', 'SDA15', 'SDA20' (SDA Retrievals)
          - 'TOT10', 'TOT15', 'TOT20' (Total Optical Depth)
    site : str, optional
        AERONET site name (exact match). If None, searches all active sites globally.
    avg_type : int
        10 = All points data, 20 = Daily averages.
    if_no_html : int
        1 = Plain text format output (recommended for automated parsing).
        
    Returns:
    --------
    pd.DataFrame containing the retrieved observations.
    """
    base_url = "https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v3"
    base_inv_url = "https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_inv_v3"
    
    params = {
        "year": start_date.year,
        "month": start_date.month,
        "day": start_date.day,
        "year2": end_date.year,
        "month2": end_date.month,
        "day2": end_date.day,
        "AVG": avg_type,
        "if_no_html": if_no_html,
        # "product": product
    }
    
    if site:
        params["site"] = site
        
    print (f"Querying AERONET Web Service ({', '.join(products)})...")
    
    data = {}
    
    for product in products:
        url = base_url
        if product in INVERSION_PRODUCTS:
            url = base_inv_url
            url_params = { **params, "product": product, "HYB20": 1 }
        else:
            url_params = { **params, product: 1 }
            
        response = requests.get ( url, params = url_params )
        response.raise_for_status()
        print (f"Successfully read from: {response.url}")
        
        # AERONET CSV payloads typically contain 6 leading header lines of metadata
        raw_text = response.text
        if "No Data Available" in raw_text or len(raw_text.strip()) == 0:
            raise ValueError ("No data available for the specified timeframe and parameters.")
        
        data[product] = raw_text
        
        
    # df = pd.read_csv(io.StringIO(raw_text), skiprows=6)
    # return df
    
    return data
    
def download_aeronet_data (
    path: str | Path,
    start_date: date,
    end_date: date,
    products: list[str] = [ "AOD15" ],
    site: str = None,
    avg_type: int = 10,
    redownload: bool = False,
    structured: bool = True
):
    files = []
    
    for day in daterange ( start_date, end_date ):
        products_to_download = []
        
        for product in products:
            filepath = aeronet_file_path (
                base_folder = path,
                measurement_date = day,
                product = product,
                structured = structured
            )
            
            folder = os.path.dirname ( filepath )
            
            if os.path.exists ( filepath ):
                if not redownload:
                    files.append ( filepath )
                    print (f"File {filepath} already exists. Will skip it because redownload option is not enabled!")
                    continue
                else:
                    print (f"Overwriting {filepath} because redownload option is enabled!")
                    
            products_to_download.append ( product )
            
        aeronet_products = fetch_aeronet_data ( day, day, products_to_download, site, avg_type )
        
        for product, raw_data in aeronet_products.items():
            filepath = aeronet_file_path (
                base_folder = path,
                measurement_date = day,
                product = product,
                structured = structured
            )
            
            folder = os.path.dirname ( filepath )
            
            if not os.path.exists ( folder ):
                os.makedirs ( folder )
            
            with open( filepath, 'w' ) as file:
                file.write ( raw_data )
                
            print ( f"Succesfully downloaded {filepath}" )
            files.append ( filepath )
            
    return files
    
def get_aeronet_dataframe (
    path: str | Path,
    start_date: datetime,
    end_date: datetime,
    products: list[str],
    stations: list[str] | None = None,
    structured: bool = True
):
    csv_dfs = []
    
    for day in daterange ( start_date, end_date ):
        for product in products:
            filepath = aeronet_file_path (
                base_folder = path,
                measurement_date = day,
                product = product,
                structured = structured
            )
            
            if os.path.exists ( filepath ):
                skiprows = 6 if product in INVERSION_PRODUCTS else 5
                csv_dfs.append (
                    pd.read_csv ( filepath, skiprows = skiprows, na_values = -999 ) # AERONET_CSV_COLUMNS_NA_VALUES )
                )
                
            
    # Just make sure candidate files are unique
    # candidate_files = list ( set ( candidate_files ) )
    
    # print ( f"Reading data from:\n\t{',\n\t'.join(candidate_files)}" )
    
    if len ( csv_dfs ) < 1:
        return pd.DataFrame()
    
    li = []
    # Join CSVs in one dataframe
    # for filepath in candidate_files:
        # df = pd.read_csv ( filepath, index_col = None, skiprows=6 )
    df = pd.concat( csv_dfs, ignore_index=True )
    
    df = pd.concat ([
        df,
        pd.DataFrame ({"Datetime": pd.to_datetime ( df["Date(dd:mm:yyyy)"] + " " + df["Time(hh:mm:ss)"], format="%d:%m:%Y %H:%M:%S" ) })
    ], axis = 1)
    # df["Datetime"] = pd.to_datetime ( df["Date(dd:mm:yyyy)"] + " " + df["Time(hh:mm:ss)"], format="%d:%m:%Y %H:%M:%S" )
    
    df = df.drop ( columns = ["Date(dd:mm:yyyy)", "Time(hh:mm:ss)"] )
    
    df = df[
         (df["Datetime"] >= start_date) &
         (df["Datetime"] <= end_date)
    ]
     
    if stations is not None:
        df = df[ df["AERONET_Site"].isin( stations ) ]
    
    return df
    
def read_aeronet_stations_file ( csv_path ):
    csv_file_path = os.path.abspath ( csv_path )
    return pd.read_csv(csv_file_path, header = 0, names = ["name", "longitude", "latitude", "altitude"])
    
def download_aeronet_files ( measurement_dates, aeronet_data_folder, temporal_threshold, redownload = False ):  
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
        
def get_aeronet_stations_with_cotemporal_data (
    xr_dataset,
    temporal_threshold,
    aeronet_stations,
    aeronet_data_folder,
    final_products,
    filtering_product = "aerosol_optical_depth_total",
    time_coordinate = "t",
    latitude_coordinate = "latitude",
    longitude_coordinate = "longitude"
):
    satellite_datetime = pd.to_datetime( xr_dataset.coords[ time_coordinate ].values[0] ).to_pydatetime( warn = False )
    
    aeronet_start_datetime = ( satellite_datetime - temporal_threshold )
    aeronet_end_datetime = ( satellite_datetime + temporal_threshold )
    
    valid_mask = xr_dataset[ filtering_product ].notnull()
    valid_lats = xr_dataset[ latitude_coord ].where( valid_mask )
    valid_lons = xr_dataset[ longitude_coord ].where(valid_mask)
    
    min_lat = float(valid_lats.min().item())
    max_lat = float(valid_lats.max().item())
    min_lon = float(valid_lons.min().item())
    max_lon = float(valid_lons.max().item())
    
    candidate_stations = aeronet_stations[
        ( aeronet_stations["latitude"] > min_lat ) &
        ( aeronet_stations["latitude"] < max_lat ) &
        ( aeronet_stations["longitude"] > min_lon ) &
        ( aeronet_stations["longitude"] < max_lon )
    ]
    
    aeronet_df = get_aeronet_dataframe (
        path = aeronet_data_folder,
        start_date = aeronet_start_datetime,
        end_date = aeronet_end_datetime,
        products = final_products,
        stations = candidate_stations["name"]
    )
    
    stations_with_data = []
    
    for idx, aeronet_station in candidate_stations.iterrows():
        station_name = aeronet_station["name"]

        # Check if there is actual data from this AERONET Site
        if aeronet_df["AERONET_Site"].where( aeronet_df['AERONET_Site'] == station_name ).count() > 0:
            stations_with_data.append ( aeronet_station )
            
    return stations_with_data