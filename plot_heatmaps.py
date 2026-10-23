RESULTS_FOLDER_REGEX = r'^([0-9]+)km_([0-9]+)min$'
RESULT_FILE_REGEX = r'^scatter_([a-zA-Z0-9_\-]+)\.json$'

DATA_VARS = [
        "r",
        "rmse",
        "slope",
        "intercept",
        "mbe",
        "mbe_pct",
        "n",
        "cr_count_g",
        "cr_pct_g",
        "cr_count_b",
        "cr_pct_b",
        "cr_count_t",
        "cr_pct_t"
]

import argparse

import numpy as np
import matplotlib.pyplot as plt
import xarray as xr
import seaborn as sns
from pathlib import Path
import json
import os
import re

import sys

def scan_result_subfolder ( folder : Path ):
    files = [ f for f in folder.iterdir () if f.is_file() ]
    
    print (files)
    
    results = []
    
    for file in files:
        match = re.search ( RESULT_FILE_REGEX, os.path.basename ( file ) )
        
        if not match:
            print ( f"File {os.path.basename ( file )} does not match REGEX {RESULT_FILE_REGEX}" )
            continue
        
        product_str = match.group(1)
        
        if not product_str:
            # This is not a valid subfolder name
            # Keep looking
            continue
            
        results.append ( (product_str, file) )
        
    return results

def build_dataset ( data_folder : Path ):   
    subfolders = [ f for f in data_folder.iterdir () if f.is_dir() ]
    
    sts = []
    tts = []
    products = []
    
    result_files = []
    
    for sf in subfolders:
        match = re.search ( RESULTS_FOLDER_REGEX, os.path.basename ( sf ) )
        
        if not match:
            continue
        
        st_str = match.group(1)
        tt_str = match.group(2)
        
        if not st_str or not tt_str:
            # This is not a valid subfolder name
            # Keep looking
            continue
            
        st = int ( st_str )
        tt = int ( tt_str )
            
        sts.append ( st )
        tts.append ( tt )

        result_files.extend (
            ( product, st, tt, file )
            for product, file
            in scan_result_subfolder ( sf )
        )
        
    sts = list ( set ( sts ) )
    sts.sort()
    
    tts = list ( set ( tts ) )
    tts.sort()
    
    products = [ rf[0] for rf in result_files ]
    products = list ( set ( products ) )
    products.sort ()
    
    print ( products )
    
    data_vars = {
        var: np.full ( ( len(products), len(sts), len(tts), ), np.nan )
        for var in DATA_VARS
    }
    
    coords = {
        "product": products,
        "spatial_threshold": sts,
        "temporal_threshold": tts
    }
    
    for product, st, tt, file in result_files:
        product_idx = products.index ( product )
        st_idx = sts.index ( st )
        tt_idx = tts.index ( tt )
        
        print ( f"Reading {file} for {product} ({st}km, {tt}mins.)" )
        
        with open ( file, 'r' ) as jf:
            # Read JSON file
            data = json.load ( jf )
            
        for p, v in data.items():
            if p not in data_vars.keys():
                # Not interested in this value
                continue
                
            data_vars[p][ product_idx ][ st_idx ][ tt_idx ] = v
    
    return xr.Dataset(
        data_vars = {
            product: ( list ( coords.keys() ), data_vars[ product ] )
            for product in data_vars.keys()
        },
        coords = coords
    )
    
def save_heatmaps ( dataset, plot_folder ):
    for product, data in dataset.groupby('product'):
        data = data.squeeze()
        
        annot_matrix = np.empty ( data["r"].shape, dtype=object )
        
        for i in range ( annot_matrix.shape[0] ):
            for j in range ( annot_matrix.shape[1] ):
                sign = "+" if data['intercept'].values[i, j] >= 0 else "-"
                regression_str = f"{data['slope'].values[i, j]:.3f}X {sign} {np.abs(data['intercept'].values[i, j]):.3f}"
                
                annot_matrix[i, j] = (
                    f"R={data['r'].values[i, j]:.3f}\n"
                    f"N={data['n'].values[i, j]}\n"
                    f"Y={regression_str}\n"
                    f"RMSE={data['rmse'].values[i, j]:.2f}\n"
                    f"MBE={data['mbe'].values[i, j]:.2f} ({data['mbe_pct'].values[i, j]:.1f}%)"
                )
                
                if product.startswith ('AOD'):
                    gcos_str = (
                        # f"\nGCOS: G={data['cr_pct_g'].values[i, j]:.2f}%, B={data['cr_pct_b'].values[i, j]:.2f}%, T={data['cr_pct_t'].values[i, j]:.2f}%"
                        f"\nGCOS={data['cr_pct_t'].values[i, j]:.2f}%"
                    )
                    
                    annot_matrix[i, j] += gcos_str
                
        # 2. Plot the base heatmap using variable 'r'
        fig, ax = plt.subplots(figsize=(12, 9))
        
        dim_y, dim_x = data["r"].dims
        
        sns.heatmap(
            data["r"].values,
            annot=annot_matrix,
            fmt="",  # Required to accept raw strings rather than numeric formatting
            cmap="viridis",
            xticklabels=data.coords[dim_x].values,
            yticklabels=data.coords[dim_y].values,
            cbar_kws={"label": "Correlation Coefficient"},
            annot_kws={"fontsize": 9},
            ax=ax,
            vmin=0,
            vmax=1
        )

        ax.set_xlabel( "Temporal threshold (minutes)" )
        ax.set_ylabel( "Spatial threshold (kilometers)" )
        ax.set_title ( product )
        plt.tight_layout()
        # plt.show()
        
        file_path = os.path.join ( plot_folder, f"heatmap_{product}.png" )
        
        plt.savefig ( file_path )

def parse_args ():
    parser = argparse.ArgumentParser()
    
    parser.add_argument ("data_folder", metavar="data-folder", help="Location of the collocation and statistical analysis")
    
    return parser.parse_args()

def main ():
    args = parse_args ()
    
    data_folder = Path ( os.path.abspath ( args.data_folder ) )
    plot_folder = Path ( os.path.join ( data_folder, "heatmaps" ) )
    
    if not os.path.exists ( plot_folder ):
        os.makedirs ( plot_folder )
    
    data = build_dataset ( data_folder )
    
    save_heatmaps ( data, plot_folder )

if __name__ == "__main__":
    main ()