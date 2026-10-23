AOD = "aod"
SSA = "ssa"
TAB = "tab"

AOD_TOTAL = "aerosol_optical_depth_total"
AOD_FINE = "aerosol_fine_mode_optical_depth"
AOD_COARSE = "aerosol_coarse_mode_optical_depth"
ANGSTROM_EXPONENT = "aerosol_optical_depth_total"
SSA_TOTAL = "aerosol_single_scattering_albedo_total"
AAOD_TOTAL = "aerosol_absorption_optical_depth_total"

RESULTS = "results"
DATETIME = "datetime"
SATELLITE_BAND = "satellite_band"
SITE = "aeronet_station"
SATELLITE_MEAN = "satellite_mean"
AERONET_MEAN = "aeronet_mean"

PLOTS_FOLDER = 'plots'
STATISTICS_FOLDER = 'statistics'

import xarray as xr
import numpy as np
from scipy.stats import gaussian_kde
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import skill_metrics as sm

from datetime import datetime
import json
import os
import sys

import argparse

import glob

def read_results_file ( path ):
    with open ( path, 'r' ) as file:
        # Read JSON file
        results = json.load ( file )
        
    return results
    
def build_aod_dataset ( results ):
    aod_data = results[ AOD ]
    
    aod_bands = []
    datetimes = []
    aeronet_sites = []
    products = [ AOD_TOTAL, AOD_FINE, AOD_COARSE ]
    
    for sat_file in aod_data:
        datetimes.append ( sat_file [ DATETIME ] )
        for product, results in sat_file[ RESULTS ].items():
            for result in results:
                if SATELLITE_BAND in result and \
                   result[ SATELLITE_BAND ] is not None:
                       
                    aod_bands.append ( result[ SATELLITE_BAND ] )
                    
                if SITE in result and \
                   result [ SITE ] is not None:
                       aeronet_sites.append ( result[ SITE ] )
                       
    aod_bands = list ( set ( aod_bands ) )
    aeronet_sites = list ( set ( aeronet_sites ) )
    
    sat_aod_total_data = np.full ( ( len(datetimes), len(aod_bands), len(aeronet_sites), ), np.nan )
    aeronet_total_aod_data = np.full ( ( len(datetimes), len(aod_bands), len(aeronet_sites), ), np.nan )
    
    sat_aod_fine_data = np.full ( ( len(datetimes), len(aod_bands), len(aeronet_sites), ), np.nan )
    aeronet_fine_aod_data = np.full ( ( len(datetimes), len(aod_bands), len(aeronet_sites), ), np.nan )
    
    sat_aod_coarse_data = np.full ( ( len(datetimes), len(aod_bands), len(aeronet_sites), ), np.nan )
    aeronet_coarse_aod_data = np.full ( ( len(datetimes), len(aod_bands), len(aeronet_sites), ), np.nan )
                    
    for sat_file in aod_data:
        for product in products:
            for result in sat_file[ RESULTS ][ product ]:
                try:
                    datetime_idx = datetimes.index ( sat_file[ DATETIME ] )
                    band_idx = aod_bands.index ( result[ SATELLITE_BAND ] )
                    site_idx = aeronet_sites.index ( result[ SITE ] )
                    
                    if product == AOD_TOTAL:
                        sat_aod_total_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ SATELLITE_MEAN ]
                        aeronet_total_aod_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ AERONET_MEAN ]
                    elif product == AOD_FINE:
                        sat_aod_fine_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ SATELLITE_MEAN ]
                        aeronet_fine_aod_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ AERONET_MEAN ]
                    elif product == AOD_COARSE:
                        sat_aod_coarse_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ SATELLITE_MEAN ]
                        aeronet_coarse_aod_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ AERONET_MEAN ]
                except ValueError, KeyError:
                    # Just leave NaN in the array
                    continue
    
    ds = xr.Dataset(
        data_vars = dict(
            satellite_aod_total = (["datetime", "band", "aeronet_site"], sat_aod_total_data),
            aeronet_aod_total = (["datetime", "band", "aeronet_site"], aeronet_total_aod_data),
            satellite_aod_fine = (["datetime", "band", "aeronet_site"], sat_aod_fine_data),
            aeronet_aod_fine = (["datetime", "band", "aeronet_site"], aeronet_fine_aod_data),
            satellite_aod_coarse = (["datetime", "band", "aeronet_site"], sat_aod_coarse_data),
            aeronet_aod_coarse = (["datetime", "band", "aeronet_site"], aeronet_coarse_aod_data),
        ),
        coords = dict(
            band = aod_bands,
            datetime = datetimes,
            aeronet_sites = aeronet_sites
        )
    )
    
    return ds
    
def build_ae_dataset ( results ):
    aod_data = results[ AOD ]

    datetimes = []
    aeronet_sites = []
    products = [ ANGSTROM_EXPONENT ]
    
    for sat_file in aod_data:
        datetimes.append ( sat_file [ DATETIME ] )
        for product, results in sat_file[ RESULTS ].items():
            for result in results:                    
                if SITE in result and \
                   result [ SITE ] is not None:
                       aeronet_sites.append ( result[ SITE ] )
                       
    aeronet_sites = list ( set ( aeronet_sites ) )
    
    sat_ae_data = np.full ( ( len(datetimes), len(aeronet_sites), ), np.nan )
    aeronet_ae_data = np.full ( ( len(datetimes), len(aeronet_sites), ), np.nan )
                    
    for sat_file in aod_data:
        for product in products:
            for result in sat_file[ RESULTS ][ product ]:
                try:
                    datetime_idx = datetimes.index ( sat_file[ DATETIME ] )
                    site_idx = aeronet_sites.index ( result[ SITE ] )
                    
                    if product == ANGSTROM_EXPONENT:
                        sat_ae_data[ datetime_idx ][ site_idx ] = result[ SATELLITE_MEAN ]
                        aeronet_ae_data[ datetime_idx ][ site_idx ] = result[ AERONET_MEAN ]
                except ValueError, KeyError:
                    # Just leave NaN in the array
                    continue
    
    ds = xr.Dataset(
        data_vars = dict(
            satellite_ae = (["datetime", "aeronet_site"], sat_ae_data),
            aeronet_ae = (["datetime", "aeronet_site"], aeronet_ae_data),
        ),
        coords = dict(
            datetime = datetimes,
            aeronet_sites = aeronet_sites
        )
    )
    
    return ds
    
def build_tab_dataset ( results ):
    aod_data = results[ TAB ]
    
    bands = []
    datetimes = []
    aeronet_sites = []
    products = [ AAOD_TOTAL ]
    
    for sat_file in aod_data:
        datetimes.append ( sat_file [ DATETIME ] )
        for product, results in sat_file[ RESULTS ].items():
            for result in results:
                if SATELLITE_BAND in result and \
                   result[ SATELLITE_BAND ] is not None:
                       
                    bands.append ( result[ SATELLITE_BAND ] )
                    
                if SITE in result and \
                   result [ SITE ] is not None:
                       aeronet_sites.append ( result[ SITE ] )
                       
    bands = list ( set ( bands ) )
    aeronet_sites = list ( set ( aeronet_sites ) )
    
    sat_aaod_total_data = np.full ( ( len(datetimes), len(bands), len(aeronet_sites), ), np.nan )
    aeronet_aaod_total_data = np.full ( ( len(datetimes), len(bands), len(aeronet_sites), ), np.nan )
                    
    for sat_file in aod_data:
        for product in products:
            for result in sat_file[ RESULTS ][ product ]:
                try:
                    datetime_idx = datetimes.index ( sat_file[ DATETIME ] )
                    band_idx = bands.index ( result[ SATELLITE_BAND ] )
                    site_idx = aeronet_sites.index ( result[ SITE ] )
                    
                    if product == AAOD_TOTAL:
                        sat_aaod_total_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ SATELLITE_MEAN ]
                        aeronet_aaod_total_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ AERONET_MEAN ]
                except ValueError, KeyError:
                    # Just leave NaN in the array
                    continue
    
    ds = xr.Dataset(
        data_vars = dict(
            satellite_aaod_total = (["datetime", "band", "aeronet_site"], sat_aaod_total_data),
            aeronet_aaod_total = (["datetime", "band", "aeronet_site"], aeronet_aaod_total_data),
        ),
        coords = dict(
            band = bands,
            datetime = datetimes,
            aeronet_sites = aeronet_sites
        )
    )
    
    return ds
    
def build_ssa_dataset ( results ):
    aod_data = results[ SSA ]
    
    bands = []
    datetimes = []
    aeronet_sites = []
    products = [ SSA_TOTAL ]
    
    for sat_file in aod_data:
        datetimes.append ( sat_file [ DATETIME ] )
        for product, results in sat_file[ RESULTS ].items():
            for result in results:
                if SATELLITE_BAND in result and \
                   result[ SATELLITE_BAND ] is not None:
                       
                    bands.append ( result[ SATELLITE_BAND ] )
                    
                if SITE in result and \
                   result [ SITE ] is not None:
                       aeronet_sites.append ( result[ SITE ] )
                       
    bands = list ( set ( bands ) )
    aeronet_sites = list ( set ( aeronet_sites ) )
    
    sat_ssa_total_data = np.full ( ( len(datetimes), len(bands), len(aeronet_sites), ), np.nan )
    aeronet_ssa_total_data = np.full ( ( len(datetimes), len(bands), len(aeronet_sites), ), np.nan )
                    
    for sat_file in aod_data:
        for product in products:
            for result in sat_file[ RESULTS ][ product ]:
                try:
                    datetime_idx = datetimes.index ( sat_file[ DATETIME ] )
                    band_idx = bands.index ( result[ SATELLITE_BAND ] )
                    site_idx = aeronet_sites.index ( result[ SITE ] )
                    
                    if product == SSA_TOTAL:
                        sat_ssa_total_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ SATELLITE_MEAN ]
                        aeronet_ssa_total_data[ datetime_idx ][ band_idx ][ site_idx ] = result[ AERONET_MEAN ]
                except ValueError, KeyError:
                    # Just leave NaN in the array
                    continue
    
    ds = xr.Dataset(
        data_vars = dict(
            satellite_ssa_total = (["datetime", "band", "aeronet_site"], sat_ssa_total_data),
            aeronet_ssa_total = (["datetime", "band", "aeronet_site"], aeronet_ssa_total_data),
        ),
        coords = dict(
            band = bands,
            datetime = datetimes,
            aeronet_sites = aeronet_sites
        )
    )
    
    return ds
    
def process_aod_total ( dataset, config ):    
    target_bias = []
    target_crmsd = []
    target_rmsd = []
    
    taylor_sdev = []
    taylor_crmsd = []
    taylor_cc = []
    
    gcos_fractions = []
    
    band_labels = []
    ref_std_captured = False
    
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_aod_total'].values
        aero_vals = data['aeronet_aod_total'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        satellite = sat_vals[valid_mask]
        aeronet = aero_vals[valid_mask]

        # Calculate Statistics
        t_stats = sm.target_statistics({'data': satellite}, {'data': aeronet}, 'data')
        tay_stats = sm.taylor_statistics({'data': satellite}, {'data': aeronet}, 'data')

        # Target Diagram Stats
        target_bias.append(float(t_stats['bias']))
        target_crmsd.append(float(t_stats['crmsd']))
        target_rmsd.append(float(t_stats['rmsd']))
        
        # Taylor Diagram Stats (Index 0 is Reference)
        if not ref_std_captured:
            taylor_sdev.append(float(tay_stats['sdev'][0]))
            taylor_crmsd.append(float(tay_stats['crmsd'][0]))
            taylor_cc.append(float(tay_stats['ccoef'][0]))
            ref_std_captured = True
            
        # Append predicted model metrics (Index 1)
        taylor_sdev.append(float(tay_stats['sdev'][1]))
        taylor_crmsd.append(float(tay_stats['crmsd'][1]))
        taylor_cc.append(float(tay_stats['ccoef'][1]))
        
        gcos_threshold = np.maximum ( config['gcos_aod_absolute'], config['gcos_aod_relative'] * aeronet )
        abs_diff = np.abs ( satellite - aeronet )
        passing_pairs = abs_diff <= gcos_threshold
        gcos_fraction = np.sum( passing_pairs ) / len ( satellite )
        
        gcos_fractions.append ( gcos_fraction )

        band_labels.append(f"{int(band)}nm" if hasattr(band, 'item') else f"{band}nm")

    # Convert to NumPy arrays
    bias_arr = np.array(target_bias)
    crmsd_arr = np.array(target_crmsd)
    rmsd_arr = np.array(target_rmsd)
    
    sdevs = np.array(taylor_sdev)
    crmsds = np.array(taylor_crmsd)
    ccs = np.array(taylor_cc)
    
    stats_file = os.path.join ( config['statistics_folder'], f"{config['spatial_threshold']}km_{config['temporal_threshold']}min_AOD_total.txt" )
    with open(stats_file, 'w') as file:
        for i, (b, c, sdev, cc, crmsd, gf, label) in enumerate(zip(bias_arr, crmsd_arr, sdevs[1:], ccs[1:], crmsds[1:], gcos_fractions, band_labels)):
            file.write ( f"@ {label}:" )
            file.write ( f"\n\tBias: {b}" )
            file.write ( f"\n\tuRMSD: {c}" )
            file.write ( f"\n\tSD: {sdev}" )
            file.write ( f"\n\tr: {cc}" )
            file.write ( f"\n\tGCOS fraction ({config['gcos_aod_absolute']}, {100 * config['gcos_aod_relative']}%): {gf}" )
            file.write ("\n")

    colors = plt.cm.tab10(np.linspace(0, 1, len(band_labels)))
    
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle("Aerosol Optical Depth (Total) Correlation")
    # fig, axes = plt.subplots( nrows = 2, figsize=(10, 8) )
    # ax_taylor = axes[0]
    # ax_target = axes[1]
    
    # ---------------------------------------------------------
    # ROW 3, LEFT: Target Diagram
    # ---------------------------------------------------------
    plt.subplot(1, 2, 1)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.target_diagram(
        bias_arr, crmsd_arr, rmsd_arr,
        markersize=0
    )
    ax_target = plt.gca()
    
    handles = []

    # Scatter overlay (X = CRMSD, Y = Bias)
    for i, (b, c, label) in enumerate(zip(bias_arr, crmsd_arr, band_labels)):
        handle = ax_target.scatter(c, b, color=colors[i], label=label, s=70, zorder=5)
        handles.append ( handle )

    # ax_target.set_title("Target Diagram", y=1.08)
    # ax_target.legend(title="Bands", loc="upper right")
    
    plt.subplot(1, 2, 2)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.taylor_diagram(
        sdevs, crmsds, ccs,
        markersize=0
    )
    ax_taylor = plt.gca()

    # Reference point
    # ref_sd = sdevs[0] if len(sdevs) > 0 else 1.0
    # ax_taylor.scatter(ref_sd, 0, color='black', marker='*', s=120, zorder=6, label='Reference')

    # Scatter overlay in polar projection (r = sdev, theta = arccos(cc))
    for i in range(len(band_labels)):
        r = sdevs[i + 1]
        theta = np.arccos(np.clip(ccs[i + 1], -1.0, 1.0))
        x_pos = r * np.cos(theta)
        y_pos = r * np.sin(theta)
        
        ax_taylor.scatter(x_pos, y_pos, color=colors[i], label=band_labels[i], s=70, zorder=5)

    # ax_taylor.set_title("Taylor Diagram", y=1.08)
    # ax_taylor.legend(title="Bands", loc="upper right")
    
    # fig, axes = plt.subplots()
    fig.legend (
        handles = handles,
        labels = band_labels,
        ncol=len(band_labels),
        loc="upper center",
        bbox_to_anchor=(.102, 0.796, 0.796, .102),
        mode="expand",
        borderaxespad=0.
    )
    
    # plt.subplots_adjust(wspace=0.5)
    plt.tight_layout(rect=[.05, .05, .95, 0.85])
    # plt.show()
    
    file_path = os.path.join ( config['plots_folder'], 'AOD_total.png' )
    
    plt.savefig ( file_path )
    plt.close()
    
def process_aod_fine ( dataset, config ):    
    target_bias = []
    target_crmsd = []
    target_rmsd = []
    
    taylor_sdev = []
    taylor_crmsd = []
    taylor_cc = []
    
    band_labels = []
    ref_std_captured = False
    
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_aod_fine'].values
        aero_vals = data['aeronet_aod_fine'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        satellite = sat_vals[valid_mask]
        aeronet = aero_vals[valid_mask]

        # Calculate Statistics
        t_stats = sm.target_statistics({'data': satellite}, {'data': aeronet}, 'data')
        tay_stats = sm.taylor_statistics({'data': satellite}, {'data': aeronet}, 'data')

        # Target Diagram Stats
        target_bias.append(float(t_stats['bias']))
        target_crmsd.append(float(t_stats['crmsd']))
        target_rmsd.append(float(t_stats['rmsd']))
        
        # Taylor Diagram Stats (Index 0 is Reference)
        if not ref_std_captured:
            taylor_sdev.append(float(tay_stats['sdev'][0]))
            taylor_crmsd.append(float(tay_stats['crmsd'][0]))
            taylor_cc.append(float(tay_stats['ccoef'][0]))
            ref_std_captured = True
            
        # Append predicted model metrics (Index 1)
        taylor_sdev.append(float(tay_stats['sdev'][1]))
        taylor_crmsd.append(float(tay_stats['crmsd'][1]))
        taylor_cc.append(float(tay_stats['ccoef'][1]))
        
        band_labels.append(f"{int(band)}nm" if hasattr(band, 'item') else f"{band}nm")

    # Convert to NumPy arrays
    bias_arr = np.array(target_bias)
    crmsd_arr = np.array(target_crmsd)
    rmsd_arr = np.array(target_rmsd)
    
    sdevs = np.array(taylor_sdev)
    crmsds = np.array(taylor_crmsd)
    ccs = np.array(taylor_cc)
    
    stats_file = os.path.join ( config['statistics_folder'], f"{config['spatial_threshold']}km_{config['temporal_threshold']}min_AOD_fine.txt" )
    with open(stats_file, 'w') as file:
        for i, (b, c, sdev, cc, crmsd, label) in enumerate(zip(bias_arr, crmsd_arr, sdevs[1:], ccs[1:], crmsds[1:], band_labels)):
            file.write ( f"@ {label}:" )
            file.write ( f"\n\tBias: {b}" )
            file.write ( f"\n\tuRMSD: {c}" )
            file.write ( f"\n\tSD: {sdev}" )
            file.write ( f"\n\tr: {cc}" )
            file.write ("\n")

    colors = plt.cm.tab10(np.linspace(0, 1, len(band_labels)))
    
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle("Aerosol Optical Depth (Fine Mode) Correlation")
    # fig, axes = plt.subplots( nrows = 2, figsize=(10, 8) )
    # ax_taylor = axes[0]
    # ax_target = axes[1]
    
    # ---------------------------------------------------------
    # ROW 3, LEFT: Target Diagram
    # ---------------------------------------------------------
    plt.subplot(1, 2, 1)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.target_diagram(
        bias_arr, crmsd_arr, rmsd_arr,
        markersize=0
    )
    ax_target = plt.gca()
    
    handles = []

    # Scatter overlay (X = CRMSD, Y = Bias)
    for i, (b, c, label) in enumerate(zip(bias_arr, crmsd_arr, band_labels)):
        handle = ax_target.scatter(c, b, color=colors[i], label=label, s=70, zorder=5)
        handles.append ( handle )

    # ax_target.set_title("Target Diagram", y=1.08)
    # ax_target.legend(title="Bands", loc="upper right")
    
    plt.subplot(1, 2, 2)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.taylor_diagram(
        sdevs, crmsds, ccs,
        markersize=0
    )
    ax_taylor = plt.gca()

    # Reference point
    # ref_sd = sdevs[0] if len(sdevs) > 0 else 1.0
    # ax_taylor.scatter(ref_sd, 0, color='black', marker='*', s=120, zorder=6, label='Reference')

    # Scatter overlay in polar projection (r = sdev, theta = arccos(cc))
    for i in range(len(band_labels)):
        r = sdevs[i + 1]
        theta = np.arccos(np.clip(ccs[i + 1], -1.0, 1.0))
        x_pos = r * np.cos(theta)
        y_pos = r * np.sin(theta)
        
        ax_taylor.scatter(x_pos, y_pos, color=colors[i], label=band_labels[i], s=70, zorder=5)

    # ax_taylor.set_title("Taylor Diagram", y=1.08)
    # ax_taylor.legend(title="Bands", loc="upper right")
    
    # fig, axes = plt.subplots()
    fig.legend (
        handles = handles,
        labels = band_labels,
        ncol=len(band_labels),
        loc="upper center",
        bbox_to_anchor=(.102, 0.796, 0.796, .102),
        mode="expand",
        borderaxespad=0.
    )
    
    # plt.subplots_adjust(wspace=0.5)
    plt.tight_layout(rect=[.05, .05, .95, 0.85])
    # plt.show()
    
    file_path = os.path.join ( config['plots_folder'], 'AOD_fine.png' )
    
    plt.savefig ( file_path )
    plt.close()

def process_aod_coarse ( dataset, config ):    
    target_bias = []
    target_crmsd = []
    target_rmsd = []
    
    taylor_sdev = []
    taylor_crmsd = []
    taylor_cc = []
    
    band_labels = []
    ref_std_captured = False
    
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_aod_coarse'].values
        aero_vals = data['aeronet_aod_coarse'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        satellite = sat_vals[valid_mask]
        aeronet = aero_vals[valid_mask]

        # Calculate Statistics
        t_stats = sm.target_statistics({'data': satellite}, {'data': aeronet}, 'data')
        tay_stats = sm.taylor_statistics({'data': satellite}, {'data': aeronet}, 'data')

        # Target Diagram Stats
        target_bias.append(float(t_stats['bias']))
        target_crmsd.append(float(t_stats['crmsd']))
        target_rmsd.append(float(t_stats['rmsd']))
        
        # Taylor Diagram Stats (Index 0 is Reference)
        if not ref_std_captured:
            taylor_sdev.append(float(tay_stats['sdev'][0]))
            taylor_crmsd.append(float(tay_stats['crmsd'][0]))
            taylor_cc.append(float(tay_stats['ccoef'][0]))
            ref_std_captured = True
            
        # Append predicted model metrics (Index 1)
        taylor_sdev.append(float(tay_stats['sdev'][1]))
        taylor_crmsd.append(float(tay_stats['crmsd'][1]))
        taylor_cc.append(float(tay_stats['ccoef'][1]))
        
        band_labels.append(f"{int(band)}nm" if hasattr(band, 'item') else f"{band}nm")

    # Convert to NumPy arrays
    bias_arr = np.array(target_bias)
    crmsd_arr = np.array(target_crmsd)
    rmsd_arr = np.array(target_rmsd)
    
    sdevs = np.array(taylor_sdev)
    crmsds = np.array(taylor_crmsd)
    ccs = np.array(taylor_cc)
    
    stats_file = os.path.join ( config['statistics_folder'], f"{config['spatial_threshold']}km_{config['temporal_threshold']}min_AOD_coarse.txt" )
    with open(stats_file, 'w') as file:
        for i, (b, c, sdev, cc, crmsd, label) in enumerate(zip(bias_arr, crmsd_arr, sdevs[1:], ccs[1:], crmsds[1:], band_labels)):
            file.write ( f"@ {label}:" )
            file.write ( f"\n\tBias: {b}" )
            file.write ( f"\n\tuRMSD: {c}" )
            file.write ( f"\n\tSD: {sdev}" )
            file.write ( f"\n\tr: {cc}" )
            file.write ("\n")

    colors = plt.cm.tab10(np.linspace(0, 1, len(band_labels)))
    
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle("Aerosol Optical Depth (Coarse Mode) Correlation")
    # fig, axes = plt.subplots( nrows = 2, figsize=(10, 8) )
    # ax_taylor = axes[0]
    # ax_target = axes[1]
    
    # ---------------------------------------------------------
    # ROW 3, LEFT: Target Diagram
    # ---------------------------------------------------------
    plt.subplot(1, 2, 1)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.target_diagram(
        bias_arr, crmsd_arr, rmsd_arr,
        markersize=0
    )
    ax_target = plt.gca()
    
    handles = []

    # Scatter overlay (X = CRMSD, Y = Bias)
    for i, (b, c, label) in enumerate(zip(bias_arr, crmsd_arr, band_labels)):
        handle = ax_target.scatter(c, b, color=colors[i], label=label, s=70, zorder=5)
        handles.append ( handle )

    # ax_target.set_title("Target Diagram", y=1.08)
    # ax_target.legend(title="Bands", loc="upper right")
    
    plt.subplot(1, 2, 2)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.taylor_diagram(
        sdevs, crmsds, ccs,
        markersize=0
    )
    ax_taylor = plt.gca()

    # Reference point
    # ref_sd = sdevs[0] if len(sdevs) > 0 else 1.0
    # ax_taylor.scatter(ref_sd, 0, color='black', marker='*', s=120, zorder=6, label='Reference')

    # Scatter overlay in polar projection (r = sdev, theta = arccos(cc))
    for i in range(len(band_labels)):
        r = sdevs[i + 1]
        theta = np.arccos(np.clip(ccs[i + 1], -1.0, 1.0))
        x_pos = r * np.cos(theta)
        y_pos = r * np.sin(theta)
        
        ax_taylor.scatter(x_pos, y_pos, color=colors[i], label=band_labels[i], s=70, zorder=5)

    # ax_taylor.set_title("Taylor Diagram", y=1.08)
    # ax_taylor.legend(title="Bands", loc="upper right")
    
    # fig, axes = plt.subplots()
    fig.legend (
        handles = handles,
        labels = band_labels,
        ncol=len(band_labels),
        loc="upper center",
        bbox_to_anchor=(.102, 0.796, 0.796, .102),
        mode="expand",
        borderaxespad=0.
    )
    
    # plt.subplots_adjust(wspace=0.5)
    plt.tight_layout(rect=[.05, .05, .95, 0.85])
    # plt.show()
    
    file_path = os.path.join ( config['plots_folder'], 'AOD_coarse.png' )
    
    plt.savefig ( file_path )
    plt.close()
    
def process_angstrom_exponent ( dataset, config ):    
    target_bias = []
    target_crmsd = []
    target_rmsd = []
    
    taylor_sdev = []
    taylor_crmsd = []
    taylor_cc = []
    
    band_labels = []
    ref_std_captured = False
    
    sat_vals = dataset['satellite_ae'].values
    aero_vals = dataset['aeronet_ae'].values
    
    valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
    
    satellite = sat_vals[valid_mask]
    aeronet = aero_vals[valid_mask]
    
    t_stats = sm.target_statistics({'data': satellite}, {'data': aeronet}, 'data')
    tay_stats = sm.taylor_statistics({'data': satellite}, {'data': aeronet}, 'data')
    
    # Target Diagram Stats
    target_bias = float(t_stats['bias'])
    target_crmsd = float(t_stats['crmsd'])
    target_rmsd = float(t_stats['rmsd'])
    
    # Append predicted model metrics (Index 1)
    taylor_sdev = float(tay_stats['sdev'][1])
    taylor_crmsd = float(tay_stats['crmsd'][1])
    taylor_cc = float(tay_stats['ccoef'][1])
    
    # Convert to NumPy arrays
    bias_arr = np.array([target_bias])
    crmsd_arr = np.array([target_crmsd])
    rmsd_arr = np.array([target_rmsd])
    
    sdevs = np.array([taylor_sdev])
    crmsds = np.array([taylor_crmsd])
    ccs = np.array([taylor_cc])
    
    band_labels = ['440-870nm']
    
    stats_file = os.path.join ( config['statistics_folder'], f"{config['spatial_threshold']}km_{config['temporal_threshold']}min_AE_440-870.txt" )
    with open(stats_file, 'w') as file:
        for i, (b, c, sdev, cc, crmsd, label) in enumerate(zip(bias_arr, crmsd_arr, sdevs, ccs, crmsds, band_labels)):
            file.write ( f"@ {label}:" )
            file.write ( f"\n\tBias: {b}" )
            file.write ( f"\n\tuRMSD: {c}" )
            file.write ( f"\n\tSD: {sdev}" )
            file.write ( f"\n\tr: {cc}" )
            file.write ("\n")
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(band_labels)))
    
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle("Angstrom Exponent (440-870nm) Correlation")

    plt.subplot(1, 2, 1)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.target_diagram(
        bias_arr, crmsd_arr, rmsd_arr,
        markersize=0
    )
    ax_target = plt.gca()
    
    handles = []

    # Scatter overlay (X = CRMSD, Y = Bias)
    for i, (b, c, label) in enumerate(zip(bias_arr, crmsd_arr, band_labels)):
        handle = ax_target.scatter(c, b, color=colors[i], label=label, s=70, zorder=5)
        handles.append ( handle )
    
    plt.subplot(1, 2, 2)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.taylor_diagram(
        sdevs, crmsds, ccs,
        markersize=0
    )
    ax_taylor = plt.gca()

    for i in range(len(band_labels)):
        r = sdevs[i]
        theta = np.arccos(np.clip(ccs[i], -1.0, 1.0))
        x_pos = r * np.cos(theta)
        y_pos = r * np.sin(theta)
        
        ax_taylor.scatter(x_pos, y_pos, color=colors[i], label=band_labels[i], s=70, zorder=5)
    
    # plt.subplots_adjust(wspace=0.5)
    plt.tight_layout(rect=[.05, .05, .95, 0.85])
    # plt.show()
    
    file_path = os.path.join ( config['plots_folder'], 'AE_440-870.png' )
    
    plt.savefig ( file_path )
    plt.close()

def process_ssa ( dataset, config ):    
    target_bias = []
    target_crmsd = []
    target_rmsd = []
    
    taylor_sdev = []
    taylor_crmsd = []
    taylor_cc = []
    
    band_labels = []
    ref_std_captured = False
    
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_ssa_total'].values
        aero_vals = data['aeronet_ssa_total'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        satellite = sat_vals[valid_mask]
        aeronet = aero_vals[valid_mask]

        # Calculate Statistics
        t_stats = sm.target_statistics({'data': satellite}, {'data': aeronet}, 'data')
        tay_stats = sm.taylor_statistics({'data': satellite}, {'data': aeronet}, 'data')

        # Target Diagram Stats
        target_bias.append(float(t_stats['bias']))
        target_crmsd.append(float(t_stats['crmsd']))
        target_rmsd.append(float(t_stats['rmsd']))
        
        # Taylor Diagram Stats (Index 0 is Reference)
        if not ref_std_captured:
            taylor_sdev.append(float(tay_stats['sdev'][0]))
            taylor_crmsd.append(float(tay_stats['crmsd'][0]))
            taylor_cc.append(float(tay_stats['ccoef'][0]))
            ref_std_captured = True
            
        # Append predicted model metrics (Index 1)
        taylor_sdev.append(float(tay_stats['sdev'][1]))
        taylor_crmsd.append(float(tay_stats['crmsd'][1]))
        taylor_cc.append(float(tay_stats['ccoef'][1]))
        
        band_labels.append(f"{int(band)}nm" if hasattr(band, 'item') else f"{band}nm")

    # Convert to NumPy arrays
    bias_arr = np.array(target_bias)
    crmsd_arr = np.array(target_crmsd)
    rmsd_arr = np.array(target_rmsd)
    
    sdevs = np.array(taylor_sdev)
    crmsds = np.array(taylor_crmsd)
    ccs = np.array(taylor_cc)
    
    stats_file = os.path.join ( config['statistics_folder'], f"{config['spatial_threshold']}km_{config['temporal_threshold']}min_SSA_total.txt" )
    with open(stats_file, 'w') as file:
        for i, (b, c, sdev, cc, crmsd, label) in enumerate(zip(bias_arr, crmsd_arr, sdevs[1:], ccs[1:], crmsds[1:], band_labels)):
            file.write ( f"@ {label}:" )
            file.write ( f"\n\tBias: {b}" )
            file.write ( f"\n\tuRMSD: {c}" )
            file.write ( f"\n\tSD: {sdev}" )
            file.write ( f"\n\tr: {cc}" )
            file.write ("\n")

    colors = plt.cm.tab10(np.linspace(0, 1, len(band_labels)))
    
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle("Aerosol Single Scattering Albedo (Total) Correlation")
    # fig, axes = plt.subplots( nrows = 2, figsize=(10, 8) )
    # ax_taylor = axes[0]
    # ax_target = axes[1]
    
    # ---------------------------------------------------------
    # ROW 3, LEFT: Target Diagram
    # ---------------------------------------------------------
    plt.subplot(1, 2, 1)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.target_diagram(
        bias_arr, crmsd_arr, rmsd_arr,
        markersize=0
    )
    ax_target = plt.gca()
    
    handles = []

    # Scatter overlay (X = CRMSD, Y = Bias)
    for i, (b, c, label) in enumerate(zip(bias_arr, crmsd_arr, band_labels)):
        handle = ax_target.scatter(c, b, color=colors[i], label=label, s=70, zorder=5)
        handles.append ( handle )

    # ax_target.set_title("Target Diagram", y=1.08)
    # ax_target.legend(title="Bands", loc="upper right")
    
    plt.subplot(1, 2, 2)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.taylor_diagram(
        sdevs, crmsds, ccs,
        markersize=0
    )
    ax_taylor = plt.gca()

    # Reference point
    # ref_sd = sdevs[0] if len(sdevs) > 0 else 1.0
    # ax_taylor.scatter(ref_sd, 0, color='black', marker='*', s=120, zorder=6, label='Reference')

    # Scatter overlay in polar projection (r = sdev, theta = arccos(cc))
    for i in range(len(band_labels)):
        r = sdevs[i + 1]
        theta = np.arccos(np.clip(ccs[i + 1], -1.0, 1.0))
        x_pos = r * np.cos(theta)
        y_pos = r * np.sin(theta)
        
        ax_taylor.scatter(x_pos, y_pos, color=colors[i], label=band_labels[i], s=70, zorder=5)

    # ax_taylor.set_title("Taylor Diagram", y=1.08)
    # ax_taylor.legend(title="Bands", loc="upper right")
    
    # fig, axes = plt.subplots()
    fig.legend (
        handles = handles,
        labels = band_labels,
        ncol=len(band_labels),
        loc="upper center",
        bbox_to_anchor=(.102, 0.796, 0.796, .102),
        mode="expand",
        borderaxespad=0.
    )
    
    # plt.subplots_adjust(wspace=0.5)
    plt.tight_layout(rect=[.05, .05, .95, 0.85])
    # plt.show()
    
    file_path = os.path.join ( config['plots_folder'], 'SSA.png' )
    
    plt.savefig ( file_path )
    plt.close()

def process_aaod ( dataset, config ):    
    target_bias = []
    target_crmsd = []
    target_rmsd = []
    
    taylor_sdev = []
    taylor_crmsd = []
    taylor_cc = []
    
    band_labels = []
    ref_std_captured = False
    
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_aaod_total'].values
        aero_vals = data['aeronet_aaod_total'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        satellite = sat_vals[valid_mask]
        aeronet = aero_vals[valid_mask]

        # Calculate Statistics
        t_stats = sm.target_statistics({'data': satellite}, {'data': aeronet}, 'data')
        tay_stats = sm.taylor_statistics({'data': satellite}, {'data': aeronet}, 'data')

        # Target Diagram Stats
        target_bias.append(float(t_stats['bias']))
        target_crmsd.append(float(t_stats['crmsd']))
        target_rmsd.append(float(t_stats['rmsd']))
        
        # Taylor Diagram Stats (Index 0 is Reference)
        if not ref_std_captured:
            taylor_sdev.append(float(tay_stats['sdev'][0]))
            taylor_crmsd.append(float(tay_stats['crmsd'][0]))
            taylor_cc.append(float(tay_stats['ccoef'][0]))
            ref_std_captured = True
            
        # Append predicted model metrics (Index 1)
        taylor_sdev.append(float(tay_stats['sdev'][1]))
        taylor_crmsd.append(float(tay_stats['crmsd'][1]))
        taylor_cc.append(float(tay_stats['ccoef'][1]))
        
        band_labels.append(f"{int(band)}nm" if hasattr(band, 'item') else f"{band}nm")

    # Convert to NumPy arrays
    bias_arr = np.array(target_bias)
    crmsd_arr = np.array(target_crmsd)
    rmsd_arr = np.array(target_rmsd)
    
    sdevs = np.array(taylor_sdev)
    crmsds = np.array(taylor_crmsd)
    ccs = np.array(taylor_cc)
    
    stats_file = os.path.join ( config['statistics_folder'], f"{config['spatial_threshold']}km_{config['temporal_threshold']}min_AAOD.txt" )
    with open(stats_file, 'w') as file:
        for i, (b, c, sdev, cc, crmsd, label) in enumerate(zip(bias_arr, crmsd_arr, sdevs[1:], ccs[1:], crmsds[1:], band_labels)):
            file.write ( f"@ {label}:" )
            file.write ( f"\n\tBias: {b}" )
            file.write ( f"\n\tuRMSD: {c}" )
            file.write ( f"\n\tSD: {sdev}" )
            file.write ( f"\n\tr: {cc}" )
            file.write ("\n")

    colors = plt.cm.tab10(np.linspace(0, 1, len(band_labels)))
    
    fig = plt.figure(figsize=(12, 6))
    fig.suptitle("Aerosol Absorption Optical Depth Correlation")
    # fig, axes = plt.subplots( nrows = 2, figsize=(10, 8) )
    # ax_taylor = axes[0]
    # ax_target = axes[1]
    
    # ---------------------------------------------------------
    # ROW 3, LEFT: Target Diagram
    # ---------------------------------------------------------
    plt.subplot(1, 2, 1)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.target_diagram(
        bias_arr, crmsd_arr, rmsd_arr,
        markersize=0
    )
    ax_target = plt.gca()
    
    handles = []

    # Scatter overlay (X = CRMSD, Y = Bias)
    for i, (b, c, label) in enumerate(zip(bias_arr, crmsd_arr, band_labels)):
        handle = ax_target.scatter(c, b, color=colors[i], label=label, s=70, zorder=5)
        handles.append ( handle )

    # ax_target.set_title("Target Diagram", y=1.08)
    # ax_target.legend(title="Bands", loc="upper right")
    
    plt.subplot(1, 2, 2)
    
    # Pass metrics and set markersize=0 to hide default markers
    sm.taylor_diagram(
        sdevs, crmsds, ccs,
        markersize=0
    )
    ax_taylor = plt.gca()

    # Reference point
    # ref_sd = sdevs[0] if len(sdevs) > 0 else 1.0
    # ax_taylor.scatter(ref_sd, 0, color='black', marker='*', s=120, zorder=6, label='Reference')

    # Scatter overlay in polar projection (r = sdev, theta = arccos(cc))
    for i in range(len(band_labels)):
        r = sdevs[i + 1]
        theta = np.arccos(np.clip(ccs[i + 1], -1.0, 1.0))
        x_pos = r * np.cos(theta)
        y_pos = r * np.sin(theta)
        
        ax_taylor.scatter(x_pos, y_pos, color=colors[i], label=band_labels[i], s=70, zorder=5)

    # ax_taylor.set_title("Taylor Diagram", y=1.08)
    # ax_taylor.legend(title="Bands", loc="upper right")
    
    # fig, axes = plt.subplots()
    fig.legend (
        handles = handles,
        labels = band_labels,
        ncol=len(band_labels),
        loc="upper center",
        bbox_to_anchor=(.102, 0.796, 0.796, .102),
        mode="expand",
        borderaxespad=0.
    )
    
    # plt.subplots_adjust(wspace=0.5)
    plt.tight_layout(rect=[.05, .05, .95, 0.85])
    # plt.show()
    
    file_path = os.path.join ( config['plots_folder'], 'AAOD.png' )
    
    plt.savefig ( file_path )
    plt.close()
    
def plot_overpass_heatmaps ( data, options ):
    sts = list ( data.keys() )
    
    tts = []
    
    for st in data.keys():
        for tt in data[st].keys():
            if tt not in tts:
                tts.append (tt)
                
    sts.sort()
    tts.sort()
    
    overpass_matrix = np.zeros ( (len(sts), len(tts)) )
    
    for i, st in enumerate ( sts ):
        for j, tt in enumerate ( tts ):
            try:
                overpass_matrix[i, j] = data[st][tt]['aod'] / data[st][tt]['satellite_files_count']
            except Exception:
                # No need to set zero, it's already initialized as such
                pass
        
    
    fig, ax = plt.subplots(figsize=(6,9))
    im = ax.imshow ( overpass_matrix, vmin=0, vmax=3 )
    
    ax.set_xticks ( range(len(tts)), labels=[f'{int(tt)}\'' for tt in tts], rotation=45 )
    ax.set_yticks ( range(len(sts)), labels=[f'{st}km' for st in sts], rotation=45 )
    
    ax.set_xlabel ( 'Time window (minutes)' )
    ax.set_ylabel ( 'Spatial threshold (kilometers)' )
    
    # Loop over data dimensions and create text annotations.
    for i in range(len(sts)):
        for j in range(len(tts)):
            text = ax.text(j, i, f'N={int(overpass_matrix[i, j] * data[st][tt]['satellite_files_count'])}\n({100 * overpass_matrix[i, j]:.1f}%)',
                           ha="center", va="center", color="w")
                           
    ax.set_title("Number of overpasses (Direct Sun Measurements)")
    fig.tight_layout()
    # plt.show()
    
    file_path = os.path.join ( options['plots_folder'], f'heatmap_overpasses_DIRECT.png' )
    
    plt.savefig ( file_path )

def generate_overpass_heatmaps ( folder, options ):
    potential_files = glob.glob ( os.path.join ( folder, "*.json" ) )
    
    overpass_data = {}
    
    # Tree hierarchy:
    # spatial_threshold -> temporal_threshold -> product_type -> overpasses (int)
    
    for json_file in potential_files:
        try:
            data = read_results_file ( json_file )
        except Exception:
            continue
            
        st = data['spatial_threshold_km']
        tt = data['temporal_threshold_minutes']
        
        if st not in overpass_data:
            overpass_data[st] = {}
        
        if tt not in overpass_data[st]:
            overpass_data[st][tt] = {
                'aod': 0,
                'ae': 0,
                'ssa': 0,
                'aaod': 0,
                'satellite_files_count': 0
            }
            
        overpass_data[st][tt]['satellite_files_count'] += len ( data[AOD] )
            
        for collocation in data[AOD]:
            overpass_data[st][tt]['aod'] += len (
                set ( [ result['aeronet_station'] for result in collocation['results']['aerosol_optical_depth_total'] ] )
            )
            
            overpass_data[st][tt]['ae'] += len (
                set ( [ result['aeronet_station'] for result in collocation['results']['aerosol_angstrom_exponent'] ] )
            )
            
        for collocation in data[SSA]:
            overpass_data[st][tt]['ssa'] += len (
                set ( [ result['aeronet_station'] for result in collocation['results']['aerosol_single_scattering_albedo_total'] ] )
            )
            
        for collocation in data[TAB]:
            overpass_data[st][tt]['aaod'] += len (
                set ( [ result['aeronet_station'] for result in collocation['results']['aerosol_absorption_optical_depth_total'] ] )
            )
            
    plot_overpass_heatmaps ( overpass_data, options )

def generate_aod_plots ( dataset, options ):
    # GCOS_ABSOLUTE_G = 0.02
    # GCOS_RELATIVE_G = 0.04
    # GCOS_ABSOLUTE_B = 0.03
    # GCOS_RELATIVE_B = 0.10
    GCOS_ABSOLUTE_T = 0.04
    GCOS_RELATIVE_T = 0.10
        
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_aod_total'].values
        aero_vals = data['aeronet_aod_total'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        x = sat_vals[valid_mask]
        y = aero_vals[valid_mask]
        
        slope, intercept = np.polyfit(x, y, 1)
        
        sign = "+" if intercept >= 0 else "-"
        
        # Calculate Statistics
        t_stats = sm.target_statistics({'data': x}, {'data': y}, 'data')
        tay_stats = sm.taylor_statistics({'data': x}, {'data': y}, 'data')
        
        bias = float ( t_stats['bias'] )
        rmsd = float ( t_stats['rmsd'] )
        r = float ( tay_stats['ccoef'][1] )
        
        xy = np.vstack ( [x, y] )
        density = gaussian_kde ( xy )( xy )
        
        sort_idx = density.argsort()
        x_sorted, y_sorted, density_sorted = x[sort_idx], y[sort_idx], density[sort_idx]
        
        # 3. Calculate validation statistics
        n = len(x)
        r = np.corrcoef(x, y)[0, 1]
        rmse = np.sqrt(np.mean((y - x) ** 2))
        mbe = np.mean(y - x)
        mbe_pct = (mbe / np.mean(x)) * 100
        
        # tolerance_g = np.maximum ( GCOS_ABSOLUTE_G, GCOS_RELATIVE_G * y )
        # tolerance_b = np.maximum ( GCOS_ABSOLUTE_B, GCOS_RELATIVE_B * y )
        tolerance_t = np.maximum ( GCOS_ABSOLUTE_T, GCOS_RELATIVE_T * y )
        
        # compliant_g = np.abs(y - x) <= tolerance_g
        # compliant_b = np.abs(y - x) <= tolerance_b
        compliant_t = np.abs(y - x) <= tolerance_t
        
        # cr_count_g = np.sum ( compliant_g )
        # cr_pct_g = (cr_count_g / n) * 100
        # cr_count_b = np.sum ( compliant_b )
        # cr_pct_b = (cr_count_b / n) * 100
        cr_count_t = np.sum ( compliant_t )
        cr_pct_t = (cr_count_t / n) * 100
        
        # 6. Plotting
        fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=150)
        
        # Scatter plot colored by density
        ax.scatter(
            x_sorted, y_sorted, c=density_sorted, cmap="jet_r", s=8, edgecolors="none"
        )
        
        # 1:1 reference line & shaded envelope
        min_val = min(min(x.min(), 0), min(y.min(), 0))
        max_val = max(x.max(), y.max())
        grid_vals = np.linspace(min_val, max_val, len(tolerance_t))

        ax.plot(grid_vals, grid_vals, "k--", lw=1.2)  # 1:1 line
        ax.fill_between(
            grid_vals,
            grid_vals - tolerance_t, # * grid_vals,
            grid_vals + tolerance_t, # * grid_vals,
            color="gray",
            alpha=0.25,
        )

        # Empirical best-fit line using calculated slope and intercept
        fit_label = (
            f"N = {n}\n"
            f"MBE = {mbe:.4f} ({mbe_pct:.1f}%)\n"
            f"Y = {slope:.3f}X {sign} {abs(intercept):.3f}\n"
            f"R = {r:.3f}  RMSE = {rmse:.3f}\n"
            # f"GCOS(G) = {cr_count_g} ({cr_pct_g:.1f}%)\n"
            # f"GCOS(B) = {cr_count_b} ({cr_pct_b:.1f}%)\n"
            f"GCOS(T) = {cr_count_t} ({cr_pct_t:.1f}%)"
        )
        ax.plot(grid_vals, slope * grid_vals + intercept, "r-", lw=1.5, label=fit_label)

        # Cosmetics matching the original figure
        ax.set_xlim(min_val, max_val)
        ax.set_ylim(min_val, max_val)
        ax.set_xlabel("GRASP Synergy", fontsize=11)
        ax.set_ylabel("AERONET", fontsize=11)
        ax.set_title(
            f"Aerosol Optical Depth {band}nm\n"
            f"({options['spatial_threshold']}km, {options['temporal_threshold']}mins.)",
            fontsize=11
        )

        ax.grid(True, linestyle="--", alpha=0.6)
        ax.tick_params(direction="in", top=True, right=True)
        ax.legend(loc="upper left", frameon=False, fontsize=8, handlelength=0, handletextpad=0)

        plt.tight_layout()
        # plt.show()
        
        file_path = os.path.join ( options['plots_folder'], f'scatter_AOD{int(band)}_total.png' )
        
        plt.savefig ( file_path )
        
        # Save statistics     
        stats_json_path = os.path.join ( options['statistics_folder'], f'scatter_AOD{int(band)}_total.json' )
        print ( stats_json_path )
        
        with open ( stats_json_path, 'w' ) as file:
            json.dump ({
                "r": r,
                "rmse": rmse,
                "slope": slope,
                "intercept": intercept,
                "mbe": mbe,
                "mbe_pct": mbe_pct,
                # "cr_count_g": int(cr_count_g),
                # "cr_pct_g": cr_pct_g,
                # "cr_count_b": int(cr_count_b),
                # "cr_pct_b": cr_pct_b,
                "cr_count_t": int(cr_count_t),
                "cr_pct_t": cr_pct_t,
                "n": n
            }, file )

def generate_ae_plots ( dataset, options ):
    
    # for band, data in dataset.groupby('band'):
    sat_vals = dataset['satellite_ae'].values
    aero_vals = dataset['aeronet_ae'].values
    
    valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
    if not np.any(valid_mask):
        return

    x = sat_vals[valid_mask]
    y = aero_vals[valid_mask]
    
    slope, intercept = np.polyfit(x, y, 1)
    
    sign = "+" if intercept >= 0 else "-"
    
    # Calculate Statistics
    t_stats = sm.target_statistics({'data': x}, {'data': y}, 'data')
    tay_stats = sm.taylor_statistics({'data': x}, {'data': y}, 'data')
    
    bias = float ( t_stats['bias'] )
    rmsd = float ( t_stats['rmsd'] )
    r = float ( tay_stats['ccoef'][1] )
    
    xy = np.vstack ( [x, y] )
    density = gaussian_kde ( xy )( xy )
    
    sort_idx = density.argsort()
    x_sorted, y_sorted, density_sorted = x[sort_idx], y[sort_idx], density[sort_idx]
    
    # 3. Calculate validation statistics
    n = len(x)
    r = np.corrcoef(x, y)[0, 1]
    rmse = np.sqrt(np.mean((y - x) ** 2))
    mbe = np.mean(y - x)
    mbe_pct = (mbe / np.mean(x)) * 100
    
    # tolerance_g = np.maximum ( GCOS_ABSOLUTE_G, GCOS_RELATIVE_G * y )
    # tolerance_b = np.maximum ( GCOS_ABSOLUTE_B, GCOS_RELATIVE_B * y )
    # tolerance_t = np.maximum ( GCOS_ABSOLUTE_T, GCOS_RELATIVE_T * y )
    
    # compliant_g = np.abs(y - x) <= tolerance_g
    # compliant_b = np.abs(y - x) <= tolerance_b
    # compliant_t = np.abs(y - x) <= tolerance_t
    
    # cr_count_g = np.sum ( compliant_g )
    # cr_pct_g = (cr_count_g / n) * 100
    # cr_count_b = np.sum ( compliant_b )
    # cr_pct_b = (cr_count_b / n) * 100
    # cr_count_t = np.sum ( compliant_t )
    # cr_pct_t = (cr_count_t / n) * 100
    
    # 6. Plotting
    fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=150)
    
    # Scatter plot colored by density
    ax.scatter(
        x_sorted, y_sorted, c=density_sorted, cmap="jet_r", s=8, edgecolors="none"
    )
    
    tolerance_t = [0] * 200
    
    # 1:1 reference line & shaded envelope
    min_val = min(min(x.min(), 0), min(y.min(), 0))
    max_val = max(x.max(), y.max())
    grid_vals = np.linspace(min_val, max_val, len(tolerance_t))

    ax.plot(grid_vals, grid_vals, "k--", lw=1.2)  # 1:1 line
    # ax.fill_between(
        # grid_vals,
        # grid_vals - tolerance_t, # * grid_vals,
        # grid_vals + tolerance_t, # * grid_vals,
        # color="gray",
        # alpha=0.25,
    # )

    # Empirical best-fit line using calculated slope and intercept
    fit_label = (
        f"N = {n}\n"
        f"MBE = {mbe:.4f} ({mbe_pct:.1f}%)\n"
        f"Y = {slope:.3f}X {sign} {abs(intercept):.3f}\n"
        f"R = {r:.3f}  RMSE = {rmse:.3f}\n"
        # f"GCOS(G) = {cr_count_g} ({cr_pct_g:.1f}%)\n"
        # f"GCOS(B) = {cr_count_b} ({cr_pct_b:.1f}%)\n"
        # f"GCOS(T) = {cr_count_t} ({cr_pct_t:.1f}%)"
    )
    ax.plot(grid_vals, slope * grid_vals + intercept, "r-", lw=1.5, label=fit_label)

    # Cosmetics matching the original figure
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)
    ax.set_xlabel("GRASP Synergy", fontsize=11)
    ax.set_ylabel("AERONET", fontsize=11)
    ax.set_title(
        f"Aerosol Angstrom Exponent 440-870nm\n"
        f"({options['spatial_threshold']}km, {options['temporal_threshold']}mins.)",
        fontsize=11
    )

    ax.grid(True, linestyle="--", alpha=0.6)
    ax.tick_params(direction="in", top=True, right=True)
    ax.legend(loc="upper left", frameon=False, fontsize=8, handlelength=0, handletextpad=0)

    plt.tight_layout()
    # plt.show()
    
    file_path = os.path.join ( options['plots_folder'], f'scatter_AE_440-870.png' )
    
    plt.savefig ( file_path )
    
    # Save statistics     
    stats_json_path = os.path.join ( options['statistics_folder'], f'scatter_AE_440-870.json' )
    
    print ( stats_json_path )
    
    with open ( stats_json_path, 'w' ) as file:
        json.dump ({
            "r": r,
            "rmse": rmse,
            "slope": slope,
            "intercept": intercept,
            "mbe": mbe,
            "mbe_pct": mbe_pct,
            # "cr_count_g": int(cr_count_g),
            # "cr_pct_g": cr_pct_g,
            # "cr_count_b": int(cr_count_b),
            # "cr_pct_b": cr_pct_b,
            # "cr_count_t": int(cr_count_t),
            # "cr_pct_t": cr_pct_t,
            "n": n
        }, file )

def generate_ssa_plots ( dataset, options ):
    # GCOS_ABSOLUTE_G = 0.02
    # GCOS_RELATIVE_G = 0.04
    # GCOS_ABSOLUTE_B = 0.03
    # GCOS_RELATIVE_B = 0.10
    # GCOS_ABSOLUTE_T = 0.06
    # GCOS_RELATIVE_T = 0.20
        
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_ssa_total'].values
        aero_vals = data['aeronet_ssa_total'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        x = sat_vals[valid_mask]
        y = aero_vals[valid_mask]
        
        slope, intercept = np.polyfit(x, y, 1)
        
        sign = "+" if intercept >= 0 else "-"
        
        # Calculate Statistics
        t_stats = sm.target_statistics({'data': x}, {'data': y}, 'data')
        tay_stats = sm.taylor_statistics({'data': x}, {'data': y}, 'data')
        
        bias = float ( t_stats['bias'] )
        rmsd = float ( t_stats['rmsd'] )
        r = float ( tay_stats['ccoef'][1] )
        
        xy = np.vstack ( [x, y] )
        density = gaussian_kde ( xy )( xy )
        
        sort_idx = density.argsort()
        x_sorted, y_sorted, density_sorted = x[sort_idx], y[sort_idx], density[sort_idx]
        
        # 3. Calculate validation statistics
        n = len(x)
        r = np.corrcoef(x, y)[0, 1]
        rmse = np.sqrt(np.mean((y - x) ** 2))
        mbe = np.mean(y - x)
        mbe_pct = (mbe / np.mean(x)) * 100
        
        # tolerance_g = np.maximum ( GCOS_ABSOLUTE_G, GCOS_RELATIVE_G * y )
        # tolerance_b = np.maximum ( GCOS_ABSOLUTE_B, GCOS_RELATIVE_B * y )
        # tolerance_t = np.maximum ( GCOS_ABSOLUTE_T, GCOS_RELATIVE_T * y )
        
        # compliant_g = np.abs(y - x) <= tolerance_g
        # compliant_b = np.abs(y - x) <= tolerance_b
        # compliant_t = np.abs(y - x) <= tolerance_t
        
        # cr_count_g = np.sum ( compliant_g )
        # cr_pct_g = (cr_count_g / n) * 100
        # cr_count_b = np.sum ( compliant_b )
        # cr_pct_b = (cr_count_b / n) * 100
        # cr_count_t = np.sum ( compliant_t )
        # cr_pct_t = (cr_count_t / n) * 100
        
        # 6. Plotting
        fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=150)
        
        # Scatter plot colored by density
        ax.scatter(
            x_sorted, y_sorted, c=density_sorted, cmap="jet_r", s=8, edgecolors="none"
        )
        
        tolerance_t = [0] * 200
        
        # 1:1 reference line & shaded envelope
        min_val = min(min(x.min(), 0), min(y.min(), 0))
        max_val = max(x.max(), y.max())
        grid_vals = np.linspace(min_val, max_val, len(tolerance_t))

        ax.plot(grid_vals, grid_vals, "k--", lw=1.2)  # 1:1 line
        # ax.fill_between(
            # grid_vals,
            # grid_vals - tolerance_t, # * grid_vals,
            # grid_vals + tolerance_t, # * grid_vals,
            # color="gray",
            # alpha=0.25,
        # )

        # Empirical best-fit line using calculated slope and intercept
        fit_label = (
            f"N = {n}\n"
            f"MBE = {mbe:.4f} ({mbe_pct:.1f}%)\n"
            f"Y = {slope:.3f}X {sign} {abs(intercept):.3f}\n"
            f"R = {r:.3f}  RMSE = {rmse:.3f}\n"
        )
        ax.plot(grid_vals, slope * grid_vals + intercept, "r-", lw=1.5, label=fit_label)

        # Cosmetics matching the original figure
        ax.set_xlim(min_val, max_val)
        ax.set_ylim(min_val, max_val)
        ax.set_xlabel("GRASP Synergy", fontsize=11)
        ax.set_ylabel("AERONET", fontsize=11)
        ax.set_title(
            f"Single Scattering Albedo {band}nm\n"
            f"({options['spatial_threshold']}km, {options['temporal_threshold']}mins.)",
            fontsize=11
        )

        ax.grid(True, linestyle="--", alpha=0.6)
        ax.tick_params(direction="in", top=True, right=True)
        ax.legend(loc="upper left", frameon=False, fontsize=8, handlelength=0, handletextpad=0)

        plt.tight_layout()
        # plt.show()
        
        file_path = os.path.join ( options['plots_folder'], f'scatter_SSA{int(band)}_total.png' )
        
        plt.savefig ( file_path )
        
        # Save statistics     
        stats_json_path = os.path.join ( options['statistics_folder'], f'scatter_SSA{int(band)}_total.json' )
        print ( stats_json_path )
        
        with open ( stats_json_path, 'w' ) as file:
            json.dump ({
                "r": r,
                "rmse": rmse,
                "slope": slope,
                "intercept": intercept,
                "mbe": mbe,
                "mbe_pct": mbe_pct,
                "n": n
            }, file )

def generate_aaod_plots ( dataset, options ):
    # GCOS_ABSOLUTE_G = 0.02
    # GCOS_RELATIVE_G = 0.04
    # GCOS_ABSOLUTE_B = 0.03
    # GCOS_RELATIVE_B = 0.10
    GCOS_ABSOLUTE_T = 0.04
    GCOS_RELATIVE_T = 0.10
        
    for band, data in dataset.groupby('band'):
        sat_vals = data['satellite_aaod_total'].values
        aero_vals = data['aeronet_aaod_total'].values
        
        valid_mask = np.isfinite(sat_vals) & np.isfinite(aero_vals)
        if not np.any(valid_mask):
            continue

        x = sat_vals[valid_mask]
        y = aero_vals[valid_mask]
        
        slope, intercept = np.polyfit(x, y, 1)
        
        sign = "+" if intercept >= 0 else "-"
        
        # Calculate Statistics
        t_stats = sm.target_statistics({'data': x}, {'data': y}, 'data')
        tay_stats = sm.taylor_statistics({'data': x}, {'data': y}, 'data')
        
        bias = float ( t_stats['bias'] )
        rmsd = float ( t_stats['rmsd'] )
        r = float ( tay_stats['ccoef'][1] )
        
        xy = np.vstack ( [x, y] )
        density = gaussian_kde ( xy )( xy )
        
        sort_idx = density.argsort()
        x_sorted, y_sorted, density_sorted = x[sort_idx], y[sort_idx], density[sort_idx]
        
        # 3. Calculate validation statistics
        n = len(x)
        r = np.corrcoef(x, y)[0, 1]
        rmse = np.sqrt(np.mean((y - x) ** 2))
        mbe = np.mean(y - x)
        mbe_pct = (mbe / np.mean(x)) * 100
        
        # tolerance_g = np.maximum ( GCOS_ABSOLUTE_G, GCOS_RELATIVE_G * y )
        # tolerance_b = np.maximum ( GCOS_ABSOLUTE_B, GCOS_RELATIVE_B * y )
        # tolerance_t = np.maximum ( GCOS_ABSOLUTE_T, GCOS_RELATIVE_T * y )
        
        # compliant_g = np.abs(y - x) <= tolerance_g
        # compliant_b = np.abs(y - x) <= tolerance_b
        # compliant_t = np.abs(y - x) <= tolerance_t
        
        # cr_count_g = np.sum ( compliant_g )
        # cr_pct_g = (cr_count_g / n) * 100
        # cr_count_b = np.sum ( compliant_b )
        # cr_pct_b = (cr_count_b / n) * 100
        # cr_count_t = np.sum ( compliant_t )
        # cr_pct_t = (cr_count_t / n) * 100
        
        # 6. Plotting
        fig, ax = plt.subplots(figsize=(5.5, 5.5), dpi=150)
        
        # Scatter plot colored by density
        ax.scatter(
            x_sorted, y_sorted, c=density_sorted, cmap="jet_r", s=8, edgecolors="none"
        )
        
        tolerance_t = [0] * 200
        
        # 1:1 reference line & shaded envelope
        min_val = min(min(x.min(), 0), min(y.min(), 0))
        max_val = max(x.max(), y.max())
        grid_vals = np.linspace(min_val, max_val, len(tolerance_t))

        ax.plot(grid_vals, grid_vals, "k--", lw=1.2)  # 1:1 line
        # ax.fill_between(
            # grid_vals,
            # grid_vals - tolerance_t, # * grid_vals,
            # grid_vals + tolerance_t, # * grid_vals,
            # color="gray",
            # alpha=0.25,
        # )

        # Empirical best-fit line using calculated slope and intercept
        fit_label = (
            f"N = {n}\n"
            f"MBE = {mbe:.4f} ({mbe_pct:.1f}%)\n"
            f"Y = {slope:.3f}X {sign} {abs(intercept):.3f}\n"
            f"R = {r:.3f}  RMSE = {rmse:.3f}\n"
        )
        ax.plot(grid_vals, slope * grid_vals + intercept, "r-", lw=1.5, label=fit_label)

        # Cosmetics matching the original figure
        ax.set_xlim(min_val, max_val)
        ax.set_ylim(min_val, max_val)
        ax.set_xlabel("GRASP Synergy", fontsize=11)
        ax.set_ylabel("AERONET", fontsize=11)
        ax.set_title(
            f"Aerosol Absorption Optical Depth {band}nm\n"
            f"({options['spatial_threshold']}km, {options['temporal_threshold']}mins.)",
            fontsize=11
        )

        ax.grid(True, linestyle="--", alpha=0.6)
        ax.tick_params(direction="in", top=True, right=True)
        ax.legend(loc="upper left", frameon=False, fontsize=8, handlelength=0, handletextpad=0)

        plt.tight_layout()
        # plt.show()
        
        file_path = os.path.join ( options['plots_folder'], f'scatter_AAOD{int(band)}_total.png' )
        
        plt.savefig ( file_path )
        
        # Save statistics     
        stats_json_path = os.path.join ( options['statistics_folder'], f'scatter_AAOD{int(band)}_total.json' )
        print ( stats_json_path )
        
        with open ( stats_json_path, 'w' ) as file:
            json.dump ({
                "r": r,
                "rmse": rmse,
                "slope": slope,
                "intercept": intercept,
                "mbe": mbe,
                "mbe_pct": mbe_pct,
                "n": n
            }, file )

def parse_args ():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--plots-folder", default=PLOTS_FOLDER, dest="plots_folder")
    parser.add_argument("--statistics-folder", default=STATISTICS_FOLDER, dest="statistics_folder")
    parser.add_argument("--gcos-aod-absolute", default=0.04, dest="gcos_aod_absolute")
    parser.add_argument("--gcos-aod-relative", default=0.10, dest="gcos_aod_relative")
    
    parser.add_argument('collocation_results_file', metavar='json-file')
            
    return parser.parse_args()

def main ():
    args = parse_args ()
    
    # Read results file
    results = read_results_file ( args.collocation_results_file )
    
    # Read somemetadata from the results
    st_km = results['spatial_threshold_km']
    tt_min = int ( results['temporal_threshold_minutes'] )
    
    print (f"Data was processed using a spatial threshold of {st_km} kilometers and a temporal threshold of {tt_min} minutes")
    
    # Convert results to xarray datasets
    aod_dataset = build_aod_dataset ( results )
    ae_dataset = build_ae_dataset ( results )
    ssa_dataset = build_ssa_dataset ( results )
    tab_dataset = build_tab_dataset ( results )
    
    plots_folder = os.path.join ( args.plots_folder, f"{st_km}km_{tt_min}min" )
    statistics_folder = os.path.join ( args.statistics_folder, f"{st_km}km_{tt_min}min" )
    
    if not os.path.exists ( plots_folder ):
        os.makedirs ( plots_folder )
    if not os.path.exists ( statistics_folder ):
        os.makedirs ( statistics_folder )
    
    # Save relevant parameters:
    options = {
        "spatial_threshold": st_km,
        "temporal_threshold": tt_min,
        "plots_folder": plots_folder,
        "statistics_folder": statistics_folder,
        "gcos_aod_absolute": args.gcos_aod_absolute,
        "gcos_aod_relative": args.gcos_aod_relative
    }
    
    # Save plots
    # if not os.path.exists ( args.plots_folder ):
        # os.makedirs ( args.plots_folder )

    # process_aod_total ( aod_dataset, options )
    # process_aod_fine ( aod_dataset, options )
    # process_aod_coarse ( aod_dataset, options )
    
    # process_angstrom_exponent ( ae_dataset, options )
    
    # process_ssa ( ssa_dataset, options )
    
    # process_aaod ( tab_dataset, options )
    
    generate_overpass_heatmaps ( os.path.dirname ( args.collocation_results_file ), options )
    
    generate_aod_plots ( aod_dataset, options )
    generate_ae_plots ( ae_dataset, options )
    generate_ssa_plots ( ssa_dataset, options )
    generate_aaod_plots ( tab_dataset, options )

if __name__ == '__main__':
    main ()