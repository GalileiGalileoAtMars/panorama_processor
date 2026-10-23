@echo off
setlocal

:: Define base paths for easy maintenance
set "SAT_FOLDER=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\satellite_data\v003"
set "AERONET_FOLDER=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\aeronet_data"
set "STATIONS_CSV=aeronet_locations.csv"
set "OUT_DIR=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\synergy-aeronet-results"

echo Starting batch collocation processing...
echo --------------------------------------------------------

:: Loop through spatial thresholds: 5, 10, 50, 100, 200
for %%s in (5 10 50 100 200) do (
    :: Loop through temporal thresholds: 15, 30, 60
    for %%t in (15 30 60) do (
        echo.
        echo [RUN] Spatial: %%s km ^| Temporal: %%t min
        echo --------------------------------------------------------
        
        python synergy_aeronet.py ^
            --satellite-folder "%SAT_FOLDER%" ^
            --aeronet-folder "%AERONET_FOLDER%" ^
            --aeronet-stations-csv "%STATIONS_CSV%" ^
            --spatial-threshold %%s ^
            --temporal-threshold %%t ^
            "%OUT_DIR%\%%skm-%%tmin.json"
            
        if errorlevel 1 (
            echo [WARNING] Run failed for spatial=%%s, temporal=%%t. Continuing...
        )
    )
)

echo.
echo ========================================================
echo All 15 collocation runs completed!
echo ========================================================
pause