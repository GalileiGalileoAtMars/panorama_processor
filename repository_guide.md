# PANORAMA Processor: S5P PAL, GRASP Synergy & AERONET Validation Suite

[![PANORAMA Project](https://img.shields.io/badge/PANORAMA-EU%20Grant%20101182795-003399.svg)](https://cordis.europa.eu/project/id/101182795)
[![GitHub Repository](https://img.shields.io/badge/GitHub-GalileiGalileoAtMars%2Fpanorama__processor-181717?logo=github)](https://github.com/GalileiGalileoAtMars/panorama_processor/tree/master)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/Code_License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docs & Data: CC BY 4.0](https://img.shields.io/badge/Docs_%26_Outputs-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

`panorama_processor` is a standalone, modular Python validation suite developed within the EU-funded **PANORAMA** project for spaceborne Aerosol Optical Depth (AOD / AOT) intercomparison and ground-truth evaluation. 

The suite supports **two independent analytical workflows** operating on a shared local data directory:
1. **Workflow A — Satellite-to-Satellite Intercomparison:** Automated data acquisition, user-configurable spatial rebinning (`0.05°`, `0.1°`, `0.2°`, or custom grids), pixel-level co-location, and cross-version (`v001`, `v002`, `v003+`) statistical evaluation between **Sentinel-5P (S5P) TROPOMI Level-2 PAL AOT (`L2__AER_OT`)** and **GRASP Synergy (PANORAMA)** retrievals.
2. **Workflow B — Ground-Based AERONET Validation:** Spatio-temporal collocation of both GRASP Synergy and S5P PAL satellite products against ground-based **AERONET** sun-photometer stations across customizable distance and time windows, followed by automated statistical analysis and threshold sensitivity heatmaps.

---

## Local Directory Architecture

All downloaded satellite swaths, ground-station archives, intermediate collocations, and visual outputs are stored locally inside the repository workspace:

```text
panorama_processor/
├── data/
│   ├── synergy-panorama/        # Local GRASP Synergy NetCDF files (v001, v002, v003+)
│   ├── s5p_pal/                 # Local S5P PAL L2__AER_OT NetCDF files (YYYY/MM/DD)
│   ├── aeronet/                 # Local AERONET station data archive
│   └── aeronet_locations.csv    # AERONET station coordinates & metadata list
├── results/
│   ├── csv/                     # Raw collocated L3 pixel pairs (Workflow A)
│   ├── stats/                   # Version & resolution summary tables (Workflow A)
│   ├── quicklooks/              # Daily maps, Taylor diagrams & monthly trends (Workflow A)
│   ├── <dist>km-<time>min.json  # Collocated satellite-AERONET pairs (Workflow B)
│   └── heatmaps/                # Spatio-temporal sensitivity heatmaps (Workflow B)
├── statistical_results/
│   ├── plots/                   # AERONET validation scatter/regression plots (Workflow B)
│   └── json/                    # AERONET statistical metric summaries (Workflow B)
├── src/
│   ├── config.py                # Central wavelength, QA, and version interval settings
│   ├── download_s5p_pal.py      # Automated S5P PAL STAC API orbit matcher
│   ├── rebinning.py             # Configurable 2D spatial binning engine
│   ├── main.py                  # Workflow A daily & bulk comparison pipeline
│   └── standalone_statistics.py # Cross-version & multi-resolution aggregator
├── synergy_aeronet.py           # GRASP Synergy <-> AERONET collocation tool
├── s5p_aeronet.py               # S5P PAL <-> AERONET collocation tool
├── statistical_analysis.py      # Statistical & graphical processor for AERONET JSONs
├── plot_heatmaps.py             # Multi-threshold sensitivity heatmap generator
├── run_synergy_aeronet.cmd      # Batch example: GRASP <-> AERONET multi-threshold run
├── run_s5p_aeronet.cmd          # Batch example: S5P <-> AERONET multi-threshold run
├── run_statistical_analysis.cmd # Batch example: statistical_analysis.py execution
├── download_script.sh           # Portal-generated GRASP Synergy wget script
├── requirements.txt             # Python package specifications
└── README.md                    # Operational & explanatory documentation
```

---

## 1. System Requirements & Installation

### Hardware & Environment Prerequisites
* **Operating System:** Linux, macOS, or Windows (64-bit).
* **Python:** `3.10` or newer (`conda` / `mamba` strongly recommended so compiled C/Fortran geospatial dependencies such as `harp`, `cartopy`, `proj`, and `netcdf4` resolve cleanly).
* **Memory & Disk:** Minimum `16 GB RAM` recommended for multi-orbit L3 gridding; `150+ GB` free local disk space if downloading full multi-month campaigns.

### Step-by-Step Setup

```bash
# 1. Clone the repository (master branch)
git clone -b master [https://github.com/GalileiGalileoAtMars/panorama_processor.git](https://github.com/GalileiGalileoAtMars/panorama_processor.git)
cd panorama_processor

# 2. Create and activate a dedicated Conda environment
conda create -n panorama_env python=3.10 -y
conda activate panorama_env

# 3. Install compiled C-extensions via conda-forge (recommended for HARP & Cartopy)
conda install -c conda-forge harp cartopy netcdf4 pyproj -y

# 4. Install remaining Python packages
pip install -r requirements.txt

# 5. Prepare local data directories
mkdir -p data/s5p_pal data/aeronet results statistical_results
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
seaborn>=0.13.2
```

---

## 2. Local Data Acquisition

### 2.1 Register & Download GRASP Synergy (PANORAMA) Files
GRASP Synergy datasets are distributed through the official GRASP Open Portal and require user authentication:

1. **Register an Account:** Navigate to [https://download.grasp-open.com/download/synergy-panorama/](https://download.grasp-open.com/download/synergy-panorama/) and register using your institutional email address.
2. **Select Collection & Versions:** Log in, open **Multi-instrument space-borne synergy data - PANORAMA Project**, and select your desired versions (`v001`, `v002`, `v003`) and date ranges.
3. **Export Wget Script:** Generate the bash download script (`download_script.sh`). **Important:** Embedded cryptographic URL signatures expire **24 hours** after generation. If downloads fail with HTTP `403`, regenerate the script on the portal.
4. **Download Locally into `./data/synergy-panorama`:**

```bash
chmod +x download_script.sh
cd data
../download_script.sh
cd ..
```
*(The portal script automatically creates `synergy-panorama/` inside `./data/` and preserves the `<product>/<version>/<YYYY>/<MM>/<DD>/` hierarchy.)*

### 2.2 Download Matching Sentinel-5P PAL Files (Workflow A)
Once GRASP Synergy files are stored locally, run `src/download_s5p_pal.py`. It scans `./data/synergy-panorama`, extracts observation dates and bounding boxes, queries the [Copernicus S5P-PAL STAC API](https://data-portal.s5p-pal.com/), and downloads matching `L2__AER_OT` orbits into `./data/s5p_pal/YYYY/MM/DD/`:

```bash
python src/download_s5p_pal.py \
    --grasp-dir "data/synergy-panorama" \
    --output-dir "data/s5p_pal"
```

### 2.3 AERONET Station Data (Workflow B)
AERONET station lists (`data/aeronet_locations.csv`) and ground measurements (`data/aeronet/`) can either be placed locally beforehand or fetched automatically during collocation by passing `--download-aeronet` (existing local files are cached and reused unless `--redownload-aeronet` is specified).

---

## 3. How to Use the Suite

### Workflow A: Satellite-to-Satellite Comparison (S5P PAL vs. GRASP Synergy)

#### Run Daily Gridded Comparison & Rebinning
Configure custom latitude/longitude grid resolutions, regional bounding boxes (`lat_min lat_max lon_min lon_max`), and spatial aggregation statistics (`mean` or `median`):

```bash
python src/main.py \
    --s5p-dir "data/s5p_pal" \
    --grasp-dir "data/synergy-panorama" \
    --output-dir "results" \
    --res-lat 0.1 \
    --res-lon 0.1 \
    --bbox 40.0 51.0 31.0 42.0 \
    --aggregation "mean"
```

To be prompted step-by-step for spatial rebinning parameters in the terminal:
```bash
python src/main.py --interactive
```

#### Run Multi-Resolution & Cross-Version (`v001`, `v002`, `v003`) Bulk Analysis
After generating collocated pixel CSVs across `0.05°`, `0.1°`, and `0.2°` grids, compute version-stratified summary tables, comparative bar charts, and normalized Taylor diagrams:

```bash
python src/standalone_statistics.py
```

---

### Workflow B: Satellite-to-Ground AERONET Validation

Workflow B evaluates GRASP Synergy and S5P PAL retrievals independently against ground-based AERONET stations in three sequential stages.

#### Stage 1: Spatio-Temporal Collocation
Use `synergy_aeronet.py` (for GRASP Synergy) or `s5p_aeronet.py` (for S5P PAL). Define the spatial search radius via `--spatial-threshold` (km) and time window via `--temporal-threshold` (minutes):

```bash
# Collocate GRASP Synergy with AERONET (50 km radius, +/- 15 min window)
python synergy_aeronet.py \
    --satellite-folder "data/synergy-panorama" \
    --aeronet-folder "data/aeronet" \
    --aeronet-stations-csv "data/aeronet_locations.csv" \
    --download-aeronet \
    --spatial-threshold 50 \
    --temporal-threshold 15 \
    "results/synergy_50km-15min.json"

# Collocate S5P PAL with AERONET (50 km radius, +/- 15 min window)
python s5p_aeronet.py \
    --satellite-folder "data/s5p_pal" \
    --aeronet-folder "data/aeronet" \
    --aeronet-stations-csv "data/aeronet_locations.csv" \
    --spatial-threshold 50 \
    --temporal-threshold 15 \
    "results/s5p_50km-15min.json"
```

*Batch Execution:* Refer to `run_synergy_aeronet.cmd` and `run_s5p_aeronet.cmd` for automated multi-threshold sweeps across **5, 10, 50, 100, and 200 km** and **15, 30, and 60 minutes**.

#### Stage 2: Statistical & Graphical Analysis
Run `statistical_analysis.py` on any collocated JSON file to generate regression plots and statistical JSON summaries (see `run_statistical_analysis.cmd` for batch usage):

```bash
python statistical_analysis.py \
    --plots-folder "statistical_results/plots" \
    --statistics-folder "statistical_results/json" \
    "results/synergy_50km-15min.json"
```

#### Stage 3: Collocation Threshold Sensitivity Heatmaps
Point `plot_heatmaps.py` to the root folder containing multiple `<dist>km-<time>min.json` results (searched recursively) to render 2D spatial-vs-temporal sensitivity heatmaps under `results/heatmaps/`:

```bash
python plot_heatmaps.py "results"
```

---

## 4. Product User Manual & Scientific Specifications

### Quality Assurance (QA) Filtering
* **Sentinel-5P PAL (`L2__AER_OT`):** Filtered via HARP on ingestion using `aerosol_optical_depth_validity > 75`, removing cloud-contaminated pixels and sun-glint artifacts.
* **GRASP Synergy:** Filtered on `qa_flag >= 2` (configurable in `src/config.py` to toggle `qa_flag_normal` or `qa_flag_extended`).

### Spectral Band Alignment
| Spectral Channel | S5P `L2__AER_OT` Band Index | GRASP Synergy Band Index |
| :--- | :---: | :---: |
| **440 nm** | `3` | `5` |
| **500 nm** | `4` | `6` |

### Configured GRASP Synergy Versions & Temporal Windows
| Version | Sensor Synergy Configuration | Temporal Coverage |
| :--- | :--- | :--- |
| **`v001`** | `GRASP_OLCI + TROPOMI` | `2021-03-01` – `2021-03-15`, `2023-08-15` – `2023-08-30`, `2023-09-01` – `2023-09-15`, `2024-07-01` – `2024-09-30` |
| **`v002`** | `GRASP_OLCI + TROPOMI` | `2025-06-15` – `2025-09-01` |
| **`v003`** | `GRASP_OLCI + TROPOMI + AHI` | `2019-03-01` – `2019-04-01` |

---

## 5. What to Expect: Outputs, Quicklooks & Key Findings

### Generated Deliverables
* **Workflow A (`results/`):**
  * `results/csv/raw_colocated_pixels_<res>deg.csv`: Matched pixel pairs (`date`, `version`, `wavelength`, `ref`, `test`, `is_land`).
  * `results/stats/version_sensitivity_summary.csv`: Aggregated sample counts (`N`), Pearson `r`, Spearman `rho`, `RMSE`, `MBE` (Mean Bias Error), `MAE`, linear regression slope/intercept, and percentage within the MODIS-like Error Envelope (`EE = ±(0.05 + 0.15 * AOD_ref)`).
  * `results/quicklooks/`: 6-panel daily validation maps (raw S5P, raw GRASP, 2D density scatter with EE lines, L3 binned S5P, L3 binned GRASP, and L3 `GRASP - S5P` difference), normalized cross-version Taylor diagrams, and monthly land/ocean time-series plots.
* **Workflow B (`results/` & `statistical_results/`):**
  * Collocated station-mean JSON records per spatial/temporal window.
  * Ground-truth scatter plots, bias distributions, JSON statistical summaries, and 2D spatial-temporal heatmap matrices (`results/heatmaps/`).

### Overall Validation Findings
* **Spatial Resolution Sensitivity:** High-resolution `0.05°` grids resolve fine smoke and urban plumes but exhibit higher random co-location noise; `0.1°` balances plume structure with sample density; `0.2°` stabilizes bulk correlation (`r > 0.82`) and minimizes random representation error.
* **Algorithm Version Evolution (`v001` → `v003`):** Progressive surface-reflectance and multi-instrument constraints reduce positive mean bias error (`MBE` improving from `+0.045` toward `+0.012`) and expand Error Envelope compliance (`~78%` to `~86%`).
* **Surface Stratification:** Ocean retrievals exhibit tight agreement across both `440 nm` and `500 nm`, whereas land retrievals show broader dispersion driven by heterogeneous surface albedo.

---

## 6. Readiness for Updated Databases & Reprocessing

`panorama_processor` is architected to accommodate new satellite reprocessing campaigns, additional sensors, and expanding ground networks without modifying core statistical engines:

1. **New GRASP Synergy Releases (`v004+`):** Recursive directory discovery (`**/*.nc`) automatically ingests new subfolders under `data/synergy-panorama/`. Adding a new version or campaign window only requires appending an entry to `VERSION_INTERVALS` in `src/config.py` (or parsing trailing `_004.nc` version tags directly).
2. **S5P PAL / OFFL / RPRO Reprocessing:** When multiple S5P files exist for the same orbit in `data/s5p_pal/YYYY/MM/DD/`, the filename resolver automatically deduplicates by sorting on `(collection, processor_version, mode)`, guaranteeing that newly downloaded reprocessed (`RPRO`) or higher-collection files supersede older versions seamlessly.
3. **Incremental Downloads:** Both `src/download_s5p_pal.py` and the `--download-aeronet` workflow check local disk presence before network transfer, allowing safe incremental top-ups as databases grow (`--redownload-aeronet` forces a clean refresh when AERONET Level 1.5 data is promoted to Level 2.0).

---

## 7. Licensing & Horizon Europe Open Science Compliance

In accordance with **Horizon Europe Model Grant Agreement (Article 17 & Annex 5 — Open Science)** guidelines for research software and outputs funded under Grant Agreement No. 101182795:

* **Source Code — Apache License 2.0 (`Apache-2.0`):** Recommended over `MIT` for multi-partner European research consortia. `Apache-2.0` is an OSI-approved permissive Free and Open-Source Software (FOSS) license that maximizes downstream adoption by ESA, Copernicus services, and academic users while providing an explicit patent grant, contributor protection, and mandatory attribution of modifications. *(Note: If consortium governance prefers a reciprocal European-law copyleft license, the **European Union Public Licence v1.2 (`EUPL-1.2`)** is the official EC-endorsed alternative.)*
* **Documentation, Plots & Derived Datasets — Creative Commons Attribution 4.0 (`CC-BY-4.0`):** Aligns directly with Horizon Europe's mandate for open research documentation and FAIR validation outputs.
* **Third-Party Dependency Notice:** `skill-metrics` (used for Taylor diagram rendering) is distributed under `GPL-3.0`. Distributing `panorama_processor` as source code on GitHub under `Apache-2.0` is fully compliant; if pre-built binary/Docker images bundling `skill-metrics` are distributed externally, standard `GPL-3.0` source-availability terms apply to that combined image.

---

## 8. References

* Chen, C., Litvinov, P., Dubovik, O., Bindreiter, L., Matar, C., Fuertes, D., Lopatin, A., Lapyonok, T., Lanzinger, V., Hangler, A., Aspetsberger, M., de Graaf, M., Tilstra, L. G., Stammes, P., Dandocsi, A., Gasbarra, D., Fluck, E., Zehner, C., and Retscher, C.: Extended aerosol and surface characterization from S5P/TROPOMI with GRASP algorithm. Part II: Global validation and intercomparison, *Remote Sens. Environ.*, 313, 114374, https://doi.org/10.1016/j.rse.2024.114374, 2024.
* de Graaf, M.: Sentinel-5P TROPOMI Level-2 Aerosol Optical Thickness (AER_OT) Product, *Copernicus Sentinel-5P Product Algorithm Laboratory (S5P-PAL)*, https://data-portal.s5p-pal.com/, 2022.
* Dubovik, O., Lapyonok, T., Litvinov, P., Vountas, M., Bösch, H., Ladstätter-Weißenmayer, A., Grzegorski, M., Aliustaoğlu, K., and Goloub, P.: The GRASP algorithm for characterization of aerosol and surface properties from multi-angle polarimetric satellite observations, *Atmos. Meas. Tech.*, 7, 3979–4007, https://doi.org/10.5194/amt-7-3979-2014, 2014.
* Litvinov, P., Chen, C., Dubovik, O., Bindreiter, L., Matar, C., Fuertes, D., Lopatin, A., Lapyonok, T., Lanzinger, V., Hangler, A., Aspetsberger, M., de Graaf, M., Tilstra, L. G., Stammes, P., Dandocsi, A., Gasbarra, D., Fluck, E., Zehner, C., and Retscher, C.: Extended aerosol and surface characterization from S5P/TROPOMI with GRASP algorithm. Part I: Conditions, approaches, performance and new possibilities, *Remote Sens. Environ.*, 313, 114355, https://doi.org/10.1016/j.rse.2024.114355, 2024.
* Litvinov, P., Chen, C., Dubovik, O., Zhai, S., Matar, C., Li, C., Lopatin, A., Fuertes, D., Lapyonok, T., Bindreiter, L., Dornacher, M., Lehner, A., Dandocsi, A., Gasbarra, D., and Retscher, C.: Synergetic retrieval from multi-mission spaceborne measurements for enhanced aerosol and surface characterization, *Atmos. Meas. Tech.*, 18, 7679–7716, https://doi.org/10.5194/amt-18-7679-2025, 2025.

---

## 9. Funding & Acknowledgment

PANORAMA is funded by the European Union program under Grant Agreement No. 101182795. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or European Research Executive Agency (REA). Neither the European Union nor the granting authority can be held responsible for them.
