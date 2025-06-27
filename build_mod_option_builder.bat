@echo off
powershell -ExecutionPolicy Bypass -File "copy_data_if_newer.ps1"
pyinstaller --noconfirm --onefile --clean --windowed --icon=assets/mod_option_builder_icon.ico --name=Mod_Option_Builder mod_option_builder.py
