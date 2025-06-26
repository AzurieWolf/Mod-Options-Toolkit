@echo off

REM Step 1: Build with PyInstaller
pyinstaller --noconfirm --onefile --clean --windowed --icon=assets/icon.ico --name=Mod_Option_Selector mod_option_selector.py

REM Step 2: Copy data folder to dist
xcopy data dist\data /E /I /Y

echo Build complete. data\ copied to dist\.
pause
