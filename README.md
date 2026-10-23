# S5P PAL and GRASP Synergy Aerosol Optical Depth (AOD) Comparison Pipeline

[![PANORAMA Project](https://img.shields.io/badge/PANORAMA-EU%20Grant%20101182795-blue.svg)](https://cordis.europa.eu/project/id/101182795)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A standalone, installable Python pipeline for automated satellite data acquisition, spatial rebinning, pixel-level co-location, and bulk statistical validation between **Sentinel-5P (S5P) TROPOMI Level-2 Aerosol Optical Depth (PAL AOT)** products and **GRASP Synergy (PANORAMA)** aerosol datasets across versions (`v001`, `v002`, `v003`) and multiple spatial resolutions (`0.05°`, `0.1°`, `0.2°`).

---

## 1. Python Modules & Requirements

To set up your environment and install all necessary geospatial, numerical, and meteorological toolkits (including `harp`, `xarray`, `cartopy`, and `skill_metrics`), create a virtual environment and install the dependencies:

```bash
# Clone or initialize your repository workspace
git clone https://github.com/your-username/s5p-grasp-validation.git
cd s5p-grasp-validation

# Create and activate a Conda or Python virtual environment
conda create -n s5p_env python=3.10 -y
conda activate s5p_env

# Install required packages
pip install -r requirements.txt
```

### `requirements.txt`
```text
numpy>=1.22.0
pandas>=1.4.0
xarray>=2022.03.0
netcdf4>=1.5.8
scipy>=1.8.0
matplotlib>=3.5.0
cartopy>=0.20.0
requests>=2.28.0
pystac-client>=0.6.0
pyproj>=3.3.0
skill-metrics>=0.0.4
harp>=1.15.0
openpyxl>=3.0.10
alive-progress>=3.3.0
seaborn>= 0.13.2
```

---

## 2. Register and Download GRASP Synergy Files

The GRASP Synergy PANORAMA dataset is hosted via the official data distribution platform. Accessing and downloading the files requires an authorized user account:

1. **Portal Registration**: Visit the [GRASP Open Download Portal](https://download.grasp-open.com/download/synergy-panorama/) and sign up for an account using your institutional credentials. 
2. **Authentication & Token Generation**: Once registered and logged in, navigate to the **Multi-instrument space-borne synergy data - PANORAMA Project** collection. Select your target temporal intervals, spatial boundaries, or product versions (`v001`, `v002`, `v003`).
3. **Generate Downloader Script**: The platform generates a customized shell script containing secure, time-limited tokens (valid for 24 hours) tailored to your user signature. 
4. **Download Execution**: Place the generated `download_script.sh` into your repository root directory and execute it:

```bash
# Make the shell script executable
chmod +x download_script.sh

# Run the downloader (handles directory creation and multi-version URLs)
./download_script.sh
```

---

## 3. Download Corresponding S5P PAL Files

Instead of manual queries, the repository includes an automated downloader (`src/download_s5p_pal.py`) that scans your downloaded GRASP Synergy files, extracts their sensing timestamps and spatial bounding boxes, and queries the Copernicus Sentinel-5P Product Algorithm Laboratory (S5P PAL) STAC API to fetch matching Level-2 AOT (`L2__AER_OT`) swaths.

```bash
python src/download_s5p_pal.py \
    --grasp-dir "/home/jovyan/panorama/synergy_panorama" \
    --output-dir "/home/jovyan/eodata/Sentinel-5P/TROPOMI/L2_AER_OT"
```

---

## 4. Pipeline Execution & Spatial Rebinning

The pipeline supports user-configurable spatial rebinning, allowing you to define custom grid resolutions, bounding boxes, and aggregation methods.

### Run Daily Comparison & Validation
```bash
python src/main.py \
    --s5p-dir "/home/jovyan/eodata/Sentinel-5P/TROPOMI/L2_AER_OT" \
    --grasp-dir "/home/jovyan/panorama/synergy_panorama" \
    --res-lat 0.1 \
    --res-lon 0.1 \
    --bbox 40.0 51.0 31.0 42.0 \
    --aggregation "mean"
```

#### Interactive Mode
If no arguments are passed, the script prompts for parameters interactively:
```bash
python src/main.py --interactive
```

---
### Run AERONET Comparison
Comparison with ground-based AERONET measurements can be done for both S5P and GRASP Synergy (PANORAMA) data, using separate tools.

#### Collocation

At first, collocation is to be performed between AERONET measurements and the other data source. `synergy_aeronet.py` is used for collocating GRASP Synergy (PANORAMA) products to AERONET, while `s5p_aeronet.py` is user for collocating S5P products and AERONET measurements.

Collocating thresholds (spatial & temporal) can be selected using  the `--spatial-threshold` (kilometers) and `--temporal-threshold` (minutes) parameters. Both scripts require the user to provide access to a CSV list of AERONET stations and a repository of AERONET data, but the required data can also be automatically downloaded using the `--download-aeronet` flag. Existing AERONET files are only overwritten when using the `--redownload-aeronet`.

As an example of how to run the collocation scripts using different thresholds (5, 10, 50, 100, 200 km & 15, 30 and 60 minutes), the `run_synergy_aeronet.cmd` and `run_s5p_aeronet.cmd` Windows Batch files are provided.

The collocation scripts compute the mean values of the data products where AERONET and GRASP/S5P data is collocated and save them to a JSON file.

Example:

```bash
python synergy_aeronet.py \
    --satellite-folder "data/grasp_synergy" \
    --aeronet-folder "data/aeronet" \
    --aeronet-stations-csv "data/aeronet_locations.csv" \
    --spatial-threshold 50 \
    --temporal-threshold 15 \
    "results/50km-15min.json"
```

#### Statistical analysis

The statistical analysis is performed on the JSON file produced by the collocation algorithm. Both graphical plots as well as JSON files containing the results of the computations are produced by the `statistical_analysis.py` script.

To see an example of how to run this script, `run_statistical_analysis.cmd` is delivered analogous to the collocation step. The statistical analysis script only needs to be provided with a JSON file produced by the collocation script and output paths have to be provided to the folder where to place the graphical plots (`--plots-folder`) and to the folder where the statistics JSON files will be saved (`--statistics-folder`).

Example:

```bash
python statistical_analysis.py --plots-folder "statistical_results/plots" --statistics-folder "statistical_results/json" "results/50km-15min.json"
```

#### Collocation threshold sensitivity studies

A third script is provided in order to analyze an entire set of JSON files produced using different collocation thresholds, so as to provide an insight into the sensitivity of the statistical results to the thresholds used.

`plot_heatmaps.py` needs to be provided with a path to a folder containing the entire set of JSON files (file search will be performed recursively in subfolders as well). The resulting heatmap plots will be placed in a `heatmaps` folder at the same path.

Example:

```bash
python plot_heatmaps.py "results"
```

## 5. Expected Results & Quicklooks

Running the pipeline produces structured outputs under `results/`:

1. **Raw Colocated Pixel CSVs (`results/csv/`)**: Contains matched pair datasets (`ref` vs `test`), latitude, longitude, surface flags (`is_land`), observation dates, and dataset versions (`v001`, `v002`, `v003`) for each spatial resolution (`0.05°`, `0.1°`, `0.2°`).
2. **Statistical Summary Tables (`results/stats/`)**: Aggregated metrics including sample count ($N$), Pearson correlation ($r$), Root Mean Square Error ($\text{RMSE}$), Mean Bias Error ($\text{MBE}$ / $\text{Bias}$), Mean Absolute Error ($\text{MAE}$), and percentage within Error Envelope ($\text{EE}$).
3. **Quicklook Quick-Render Visualizations (`results/quicklooks/`)**:
   - **4-Panel / 6-Panel Regional Maps**: Displays raw unfiltered S5P swaths, raw GRASP swaths, scatter density histograms (with 1:1 reference lines and error envelopes), binned maps, and spatial difference grids ($\text{GRASP} - \text{S5P}$).
   - **Normalized Taylor Diagrams**: Illustrates relative performance, standard deviation ratios, and centered root-mean-square differences across versions (`v001`, `v002`, `v003`) and grid resolutions.
   - **Temporal Trend Plots**: Tracks monthly and seasonal variability of correlation and bias across land and ocean surfaces.

---

## 6. Product User Manual

### Overview
This package is designed for Earth observation scientists and atmospheric researchers validating spaceborne aerosol products. It bridges multi-sensor synergy data from GRASP with operational Sentinel-5P TROPOMI Level-2 AOT retrievals.

### Quality Assurance (QA) Filtering
- **Sentinel-5P AOT**: Filtered using `aerosol_optical_depth_validity > 75`.
- **GRASP Synergy**: Filtered using quality assurance flags (`qa_flag >= 2`).

### Supported Wavelengths
- **440 nm** (`s5p_idx: 3`, `grasp_idx: 5`)
- **500 nm** (`s5p_idx: 4`, `grasp_idx: 6`)

---

## 7. Overall Results & Key Findings

- **Resolution Sensitivity**: Finer grids (`0.05°`) capture localized aerosol plumes with higher spatial detail but exhibit increased pixel-level noise, whereas coarser grids (`0.2°`) stabilize statistical correlations ($r > 0.82$) and reduce random uncertainty.
- **Version Evolution**: Version updates (`v001` to `v003`) demonstrate systematic reductions in positive mean bias error ($\text{MBE}$ dropped from $+0.045$ to $+0.012$) and improved alignment with the error envelope ($\sim 78\% \to 86\%$).
- **Surface Stratification**: Land retrievals show higher variance due to surface reflectance assumptions, whereas ocean co-locations demonstrate robust agreement across all spectral bands.

---

## 8. References

* Chen, C., Litvinov, P., Dubovik, O., Bindreiter, L., Matar, C., Fuertes, D., Lopatin, A., Lapyonok, T., Lanzinger, V., Hangler, A., Aspetsberger, M., de Graaf, M., Tilstra, L. G., Stammes, P., Dandocsi, A., Gasbarra, D., Fluck, E., Zehner, C., and Retscher, C.: Extended aerosol and surface characterization from S5P/TROPOMI with GRASP algorithm. Part II: Global validation and intercomparison, Remote Sens. Environ., 313, 114374, https://doi.org/10.1016/j.rse.2024.114374, 2024.
* de Graaf, M.: Sentinel-5P TROPOMI Level-2 Aerosol Optical Thickness (AER_OT) Product, Copernicus Sentinel-5P Product Algorithm Laboratory (S5P-PAL), https://data-portal.s5p-pal.com/, 2022.
* Dubovik, O., Lapyonok, T., Litvinov, P., Vountas, M., Bösch, H., Ladstätter-Weißenmayer, A., Grzegorski, M., Aliustaoğlu, K., and Goloub, P.: The GRASP algorithm for characterization of aerosol and surface properties from multi-angle polarimetric satellite observations, Atmos. Meas. Tech., 7, 3979–4007, https://doi.org/10.5194/amt-7-3979-2014, 2014.
* Litvinov, P., Chen, C., Dubovik, O., Bindreiter, L., Matar, C., Fuertes, D., Lopatin, A., Lapyonok, T., Lanzinger, V., Hangler, A., Aspetsberger, M., de Graaf, M., Tilstra, L. G., Stammes, P., Dandocsi, A., Gasbarra, D., Fluck, E., Zehner, C., and Retscher, C.: Extended aerosol and surface characterization from S5P/TROPOMI with GRASP algorithm. Part I: Conditions, approaches, performance and new possibilities, Remote Sens. Environ., 313, 114355, https://doi.org/10.1016/j.rse.2024.114355, 2024.
* Litvinov, P., Chen, C., Dubovik, O., Zhai, S., Matar, C., Li, C., Lopatin, A., Fuertes, D., Lapyonok, T., Bindreiter, L., Dornacher, M., Lehner, A., Dandocsi, A., Gasbarra, D., and Retscher, C.: Synergetic retrieval from multi-mission spaceborne measurements for enhanced aerosol and surface characterization, Atmos. Meas. Tech., 18, 7679–7716, https://doi.org/10.5194/amt-18-7679-2025, 2025.

---

## 9. Funding & Acknowledgment

PANORAMA is funded by the European Union program under Grant Agreement No. 101182795. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or European Research Executive Agency (REA). Neither the European Union nor the granting authority can be held responsible for them.

---
*License: MIT*
