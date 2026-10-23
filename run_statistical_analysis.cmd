@echo off
setlocal

:: Define output folders
set "PLOTS_FOLDER=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\results_v002"
set "STATS_FOLDER=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\results_v002"
set "OUT_FOLDER=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\synergy-statistics"

:: Loop through spatial values (in km)
for %%s in (5 10 50 100 200) do (
    :: Loop through temporal values (in min)
    for %%t in (15 30 60) do (
        echo ===================================================
        echo Processing: %%skm and %%tmin...
        echo ===================================================
        
        python statistical_analysis.py --plots-folder "%PLOTS_FOLDER%" --statistics-folder "%STATS_FOLDER%" "%OUT_FOLDER%\%%skm-%%tmin.json"
        
        if errorlevel 1 (
            echo [WARNING] An error occurred while processing %%skm-%%tmin.
        )
        echo.
    )
)

echo All 15 combinations have been processed!
endlocal
pause