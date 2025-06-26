# Step 1: Build with PyInstaller
pyinstaller --noconfirm --onefile --clean --windowed --icon=assets/icon.ico --name=Mod_Option_Builder mod_option_builder.py

# Step 2: Copy data folder to dist
Copy-Item -Recurse -Force data dist\data

Write-Host "Build complete. data/ copied to dist/."
