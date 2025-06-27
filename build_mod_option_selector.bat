@echo off
powershell -ExecutionPolicy Bypass -File "copy_data_if_newer.ps1"
pyinstaller --noconfirm --onefile --clean --windowed --icon=assets/mod_option_selector_icon.ico --name=Mod_Option_Selector mod_option_selector.py
