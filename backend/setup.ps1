# Saffron India Backend Setup Script
# Run this script in PowerShell from the backend directory

Write-Host "Setting up Python virtual environment..." -ForegroundColor Cyan

# Create virtual environment
python -m venv venv

Write-Host "Virtual environment created!" -ForegroundColor Green

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

Write-Host "`nSetup complete! Virtual environment is now active." -ForegroundColor Green
Write-Host "To activate it again later, run: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow

