# Synergy Satellite (GRASP PANORAMA) and S5P PAL Analysis

This repository contains a ready-to-install Python package and pipeline for processing, spatially rebinning, and comparing multi-instrument space-borne synergy data (OLCI, TROPOMI, AHI) from the GRASP PANORAMA Project alongside corresponding Sentinel-5 Precursor (S5P) Product Algorithm Laboratory (PAL) files.

## 1\. Installation & Requirements

To run the analysis, you will need Python 3.8+ and several scientific computing libraries.

Clone this repository and install the dependencies using `pip`:

```
git clone https://github.com/your-org/synergy-s5p-analysis.git
cd synergy-s5p-analysis
pip install -r requirements.txt

```

&nbsp;

## 2\. Downloading Data

### 2.1 Downloading GRASP Synergy Satellite Files

The repository uses `download_script.sh` to automate the downloading of the PANORAMA synergy files (`.nc` format).

1. Make the script executable and run it:

```
chmod +x download_script.sh
./download_script.sh

```

   *(Note: The script creates a directory structure starting with `synergy-panorama/`. Remember that GRASP portal URLs expire after 24 hours).*

### 2.2 Automated S5P PAL Downloader (Matching GRASP Synergy)

Instead of manually querying the portal, you can use the included `src/download_s5p_pal.py` script. This script scans your local `synergy-panorama/` directory, extracts the exact timestamps and spatial bounding boxes from the GRASP NetCDF files, and queries the S5P PAL STAC API to download matching products automatically.

Run the automated downloader:

```
python src/download_s5p_pal.py --synergy-dir ./synergy-panorama --output-dir ./data/s5p_pal --product L2__AER_AI

```

&nbsp;

## 3\. Running the Pipeline & Spatial Rebinning

The main pipeline (`src/main.py`) ingests both datasets, rebins them onto a common regular latitude/longitude grid, and performs daily statistical comparisons. Users can customize the **spatial rebinning resolution** and **bounding box** via command-line arguments.

### Usage & Spatial Rebinning Options

```
python src/main.py \
  --date 2023-05-15 \
  --res-lat 0.25 \
  --res-lon 0.25 \
  --bbox -20.0 30.0 40.0 70.0 \
  --method mean

```

&nbsp;

**Parameters:**

* `--date`: Target date for daily comparison in `YYYY-MM-DD` format (or `ALL` to process all available dates).

* `--res-lat`: Target grid latitude resolution in degrees (default: `0.1`).

* `--res-lon`: Target grid longitude resolution in degrees (default: `0.1`).

* `--bbox`: Spatial bounding box as `MIN_LON MIN_LAT MAX_LON MAX_LAT` (default: `-180 -90 180 90`).

* `--method`: Aggregation method for spatial rebinning (`mean`, `median`, or `nearest`).

## 4\. Examples of Daily Comparison

### Example 1: High-Resolution Regional Daily Comparison (Europe)

To compare Aerosol Optical Depth (AOD) and Aerosol Index (AI) over Europe on June 12, 2023, rebinned to a fine $0.{1}^{\circ }\times 0.{1}^{\circ }$ grid using median aggregation to filter out cloud-edge outliers:

```
python src/main.py --date 2023-06-12 --res-lat 0.1 --res-lon 0.1 --bbox -15.0 35.0 35.0 65.0 --method median

```

&nbsp;

### Example 2: Coarse Global Daily Overview

To generate a fast daily comparison across a broader synoptic scale at $0.{5}^{\circ }\times 0.{5}^{\circ }$ resolution:

```
python src/main.py --date 2023-07-01 --res-lat 0.5 --res-lon 0.5 --method mean

```

&nbsp;

## 5\. Expected Results & Quicklooks

All outputs are systematically saved in the `results/` directory, organized by date and grid resolution.

### 5.1 Collocated & Rebinned NetCDF Files (`results/nc/`)

* **Filename format:** `collocated_GRASP_S5PPAL_YYYYMMDD_res{LAT}x{LON}.nc`

* **Dimensions:** `lat`, `lon`, `time`

* **Variables included:**

  * `grasp_aod_550`: Rebinned GRASP Synergy Aerosol Optical Depth at 550 nm.

  * `grasp_aod_std`: Standard deviation of GRASP pixels falling within each grid cell.

  * `s5p_pal_val`: Rebinned S5P PAL target variable (e.g., UV Aerosol Index or $\text{NO}_2$ tropospheric column).

  * `pixel_count`: Number of valid native satellite pixels aggregated per grid cell.

  * `absolute_difference`: Grid-level difference ($\text{GRASP} - \text{S5P PAL}$).

### 5.2 Statistical Summary Tables (`results/stats/`)

* **Filename format:** `daily_stats_YYYYMMDD.csv`

* **Contents:** Daily tabular metrics including Pearson correlation coefficient ($r$), Root Mean Square Error ($\text{RMSE}$), Mean Bias Error ($\text{MBE}$), linear regression slope/intercept, and total number of valid collocated grid cells ($N$).

### 5.3 Visual Quicklooks (`results/quicklooks/`)

For every processed day, the pipeline automatically generates a 4-panel high-resolution quicklook figure (`quicklook_YYYYMMDD_res{LAT}x{LON}.png`):

1. **Top-Left Panel:** Spatial map of rebinned GRASP Synergy data with coastlines and gridlines.

2. **Top-Right Panel:** Spatial map of rebinned S5P PAL data over the identical bounding box.

3. **Bottom-Left Panel:** Spatial Difference Map ($\Delta = \text{GRASP} - \text{S5P}$) using a diverging colormap (`RdBu_r`) to highlight regional biases.

4. **Bottom-Right Panel:** 2D Density Scatter Plot comparing GRASP vs. S5P PAL values, overlaid with the $1:1$ reference line, linear regression fit, and embedded statistical summary box ($r, \text{RMSE}, N$).

## 6\. References & Data Citation

When utilizing or citing data products processed through this repository, please reference the corresponding mission algorithms and product laboratories:

### GRASP Synergy & Multi-Pixel Retrieval

* **General Retrieval Algorithm:** Dubovik, O., et al. (2011). "Application of general retrieval approach to remote sensing of precipitation and atmospheric aerosols." *Atmospheric Measurement Techniques*, 4(5), 947–984. DOI: [10.5194/amt-4-947-2011](https://doi.org/10.5194/amt-4-947-2011).

* **Multi-Pixel Synergy Methodology:** Dubovik, O., et al. (2014). "Statistically optimized inversion algorithm for enhanced retrieval of aerosol properties from spectral multi-pixel remote sensing." *Atmospheric Measurement Techniques*, 7(10), 3253–3280. DOI: [10.5194/amt-7-3253-2014](https://doi.org/10.5194/amt-7-3253-2014).

* **S5P/TROPOMI GRASP Algorithm & Performance (Part I):** Litvinov, P., Chen, C., Dubovik, O., Bindreiter, L., Matar, C., Fuertes, D., Lopatin, A., Lapyonok, T., Lanzinger, V., Hangler, A., Aspetsberger, M., de Graaf, M., Tilstra, L. G., Stammes, P., Dandocsi, A., Gasbarra, D., Fluck, E., Zehner, C., and Retscher, C. (2024). Extended aerosol and surface characterization from S5P/TROPOMI with GRASP algorithm. Part I: Conditions, approaches, performance and new possibilities. *Remote Sensing of Environment*, Volume 313, 114355\. DOI: [10.1016/j.rse.2024.114355](https://doi.org/10.1016/j.rse.2024.114355).

* **S5P/TROPOMI GRASP Algorithm & Performance (Part II):** Chen, C., Litvinov, P., Dubovik, O., Bindreiter, L., Matar, C., Fuertes, D., Lopatin, A., Lapyonok, T., Lanzinger, V., Hangler, A., Aspetsberger, M., de Graaf, M., Tilstra, L. G., Stammes, P., Dandocsi, A., Gasbarra, D., Fluck, E., Zehner, C., and Retscher, C. (2024). Extended aerosol and surface characterization from S5P/TROPOMI with GRASP algorithm. Part II: Global validation and intercomparison. *Remote Sensing of Environment*, Volume 313, 114374\. DOI: [10.1016/j.rse.2024.114374](https://doi.org/10.1016/j.rse.2024.114374).

* **Recent Synergy & Algorithm Developments:** Litvinov, P., Chen, C., Dubovik, O., Zhai, S., Matar, C., Li, C., Lopatin, A., Fuertes, D., Lapyonok, T., Bindreiter, L., Dornacher, M., Lehner, A., Dandocsi, A., Gasbarra, D., and Retscher, C. (2025). Synergetic retrieval from multi-mission spaceborne measurements for enhanced aerosol and surface characterization. *Atmospheric Measurement Techniques*, 18, 7679–7716. DOI: [10.5194/amt-18-7679-2025](https://doi.org/10.5194/amt-18-7679-2025).

* **PANORAMA Project:** GRASP SAS / Université de Lille (2022). *PANORAMA Project: Multi-instrument satellite synergy datasets for aerosol and surface characterization*. Available via the GRASP Data Portal.

### S5P PAL (Product Algorithm Laboratory)

* **Mission Overview:** Veefkind, J. P., et al. (2012). "TROPOMI on the Sentinel-5 Precursor: A operational method for monitoring the atmospheric composition from space." *Remote Sensing of Environment*, 120, 70–83. DOI: [10.1016/j.rse.2011.09.027](https://doi.org/10.1016/j.rse.2011.09.027).

* **S5P-PAL AOD Product:** de Graaf, M. (2022). *Sentinel-5P TROPOMI Level-2 Aerosol Optical Thickness (AER\_OT) Product*. Copernicus Sentinel-5P Product Algorithm Laboratory (S5P-PAL). Available online: [https\://data-portal.s5p-pal.com/](https://data-portal.s5p-pal.com/).

* **PAL Data Portal & STAC Access:** European Space Agency (ESA) / Royal Netherlands Meteorological Institute (KNMI) (2023). *Sentinel-5 Precursor Product Algorithm Laboratory (S5P PAL) Data Portal & STAC API*. Available online: [https\://data-portal.s5p-pal.com](https://data-portal.s5p-pal.com).

## 7\. Acknowledgments

This work is supported by the PANORAMA project and is funded by the European Union program under Grant Agreement No. 101182795\. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or European Research Executive Agency (REA). Neither the European Union nor the granting authority can be held responsible for them.

## 8\. Repository Directory Structure

```
├── README.md                  # Product User Manual and documentation
├── requirements.txt           # Python dependencies
├── download_script.sh         # Bash script for GRASP PANORAMA data
├── synergy-panorama/          # Raw GRASP NetCDF files
├── data/
│   └── s5p_pal/               # Raw S5P PAL NetCDF files (populated by downloader)
├── results/
│   ├── nc/                    # Rebinned & collocated NetCDF outputs
│   ├── stats/                 # Daily CSV statistical summaries
│   └── quicklooks/            # Daily 4-panel PNG comparison plots
└── src/
    ├── config.py              # Default parameters and variable mappings
    ├── download_s5p_pal.py    # Automated S5P PAL STAC downloader matching GRASP
    ├── rebinning.py           # 2D spatial binning engine (scipy/xarray)
    └── main.py                # CLI entry point and daily comparison workflow

```

&nbsp;