@echo off
setlocal

:: Define output folders
set "RESULTS_FOLDER=C:\Users\ihlad\Desktop\Stuff\Projects\PANORAMA\synergy-statistics"

echo ===================================================
echo Processing: %RESULTS_FOLDER%...
echo ===================================================

python plot_heatmaps.py %RESULTS_FOLDER%"

if errorlevel 1 (
	echo [WARNING] An error occurred while processing folder %RESULTS_FOLDER%.
)
echo.

endlocal
pause