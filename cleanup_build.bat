@echo off
echo Cleaning up build artifacts...
echo.

echo Stopping any running processes...
taskkill /f /im YouTubeMonitorGUI.exe 2>nul
taskkill /f /im python.exe 2>nul

echo.
echo Removing build directories...
if exist build (
    rmdir /s /q build
    echo Removed build directory
) else (
    echo Build directory not found
)

if exist dist (
    rmdir /s /q dist
    echo Removed dist directory
) else (
    echo Dist directory not found
)

echo.
echo Cleanup completed!
echo You can now run build_exe.py again
pause
