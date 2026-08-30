@echo off
REM Saffron India Backend Setup Script
REM Run this script from the backend directory

echo Setting up Python virtual environment...

python -m venv venv

echo Virtual environment created!
echo Activating virtual environment...

call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! Virtual environment is now active.
echo To activate it again later, run: venv\Scripts\activate.bat
pause

