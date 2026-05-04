@echo off
:: Di chuyển vào thư mục chứa file .bat này
cd /d "%~dp0"

echo [STEP 1] Downloading Market Data...
call python data_loader.py --filename "vic.history.csv"

echo [STEP 2] Seeding Market Data to MySQL...
call python seed_market_data.py

echo [STEP 3] Generating Investor Data...
call python investor_data_generation.py

pause