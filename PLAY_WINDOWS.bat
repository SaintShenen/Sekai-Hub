@echo off
title Sekai-Hub Launcher
echo ==================================================
echo        INITIALIZING SEKAI-HUB RPG ENGINE
echo ==================================================
echo.
echo [1/2] Checking for updates and installing libraries...
pip install -r requirements.txt
echo.
echo [2/2] Launching Simulation...
echo.
echo NOTE: A browser window will open shortly.
echo Do not close this black window while playing!
echo.
streamlit run app.py
pause