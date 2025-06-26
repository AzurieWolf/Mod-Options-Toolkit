# Mod Option Toolkit

A two-part mod management toolkit: Mod Option Builder lets you create and organize mod packages, while Mod Option Selector provides a user-friendly way to preview, install, and manage those mods with visual feedback and customization.

## 🔧 Mod Option Builder

**Mod Option Builder** is a GUI-based tool that allows you to create, organize, and package mod options into a structured JSON format. Key features include:

* 📝 Create and manage mod entries with title, description, and metadata.
* 📦 Associate ZIP archives and preview images for each mod.
* 🔍 Automatically extract and list files from ZIPs.
* 🖼️ Preview mod images inside the application.
* 🧩 Define important metadata like `chunk_id` and `replaces` fields.
* 💾 Save all configuration data to `mod_options.json`.
* 📁 Package everything into a distributable mod ZIP, including the selector executable.

## 🧩 Mod Option Selector

**Mod Option Selector** is the user-facing side of the toolkit. It allows users to easily browse, preview, and install mod packages. Features include:

* 🌙 Dark-themed UI with full theme support.
* 🔍 Live preview of each mod's image, metadata, and description.
* ✅ Visual indicators for installed mods, missing files, or incomplete info:

  * ✔️ Installed
  * ⚠️ Missing information
  * ❌ Invalid or empty
* 📂 Install and uninstall mods with one click.
* 🔄 Auto-refresh when the `mod_options.json` file changes.
* 🧠 Smart settings:

  * Allow or prevent multiple installs.
  * Enable/disable confirmation prompts.
  * Set and manage install directories.
* ⚙️ Built-in settings and about windows.
* 🔁 Direct access to launch the Mod Option Builder from within the Selector.

## 📁 File Structure

```
data/
  ├── mod_options.json        # Mod entries created by the builder
  ├── settings.json           # Selector settings
  ├── theme.json              # Theme configuration
  └── zips/
      ├── *.zip               # Mod ZIP files
      └── previews/           # Mod preview images

Mod_Option_Builder.exe        # Builder executable
Mod_Option_Selector.exe       # Selector executable
```

## 🛠 Author

Created by [AzurieWolf](https://linktr.ee/azuriewolf)
GitHub: [github.com/azuriewolf](https://github.com/azuriewolf)