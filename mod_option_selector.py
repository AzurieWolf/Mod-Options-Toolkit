import json            # For reading/writing JSON files (settings, zip data, theme)
import subprocess  # For launching external applications
import os              # For file and path operations
import zipfile         # To handle zip files (extracting them)
import sys             # To exit the program on errors
import tempfile        # To get temp directory for lock file
import msvcrt          # For Windows file locking (prevent multiple instances)
import webbrowser
from tkinter import (
    Tk, Canvas, filedialog, Scrollbar, Frame, RIGHT, BOTH, Y,
    messagebox, Toplevel, StringVar, BooleanVar, ttk, font, Label, StringVar
)
# GUI toolkit (Tkinter) and submodules for widgets, dialogs, and styling
from PIL import Image, ImageTk  # For image handling and displaying in Tkinter

# Define a lock file path in temp directory to prevent multiple app instances
lock_file_path = os.path.join(tempfile.gettempdir(), "mod_option_selector.lock")

try:
    # Try to create and lock the file exclusively
    lock_file = open(lock_file_path, "w")
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    # If lock fails, app is already running, so show error and quit
    messagebox.showerror("Already Running", "The application is already running.")
    sys.exit()

# File paths for settings, zip package metadata, and theme configuration
SETTINGS_FILE = 'data/settings.json'
OPTIONS_FILE = 'data/mod_options.json'
THEME_FILE = 'data/theme.json'

class ModOptionSelectorApp:
    def __init__(self, master):
        self.master = master
        
        # App display name and version
        self.app_name = "Mod Option Selector"
        self.app_version = "1.0.0"
        self.app_author = "AzurieWolf"
        self.app_author_weblink = "https://linktr.ee/azuriewolf"
        self.app_github_weblink = "https://github.com/AzurieWolf/Mod-Option-Toolkit"

        # Set window title with app name and version
        master.title(self.app_name + " v" + self.app_version + " by " + self.app_author)

        # Load user settings, theme, and zip metadata from files
        self.load_settings()
        self.load_theme()
        self.load_zip_data()

        self.last_zip_data_mtime = os.path.getmtime(OPTIONS_FILE)
        self.master.after(2000, self.check_mod_options_data_changes)  # Check every 2 second

        # Set background color according to theme or default dark gray
        master.configure(bg=self.theme.get("background", "#2e2e2e"))

        # Setup ttk widget styles based on the theme
        self.set_theme_style()

        # Load check icon image for installed items, resize to 16x16 px
        self.check_image = ImageTk.PhotoImage(Image.open("data/assets/check.ico").resize((16, 16)))
        # Load error icon image for mods with no files detected, resize to 16x16 px
        self.error_image = ImageTk.PhotoImage(Image.open("data/assets/error.ico").resize((16, 16)))
        # Load caution icon image for mods with missing information, resize to 16x16 px
        self.caution_image = ImageTk.PhotoImage(Image.open("data/assets/caution.ico").resize((16, 16)))
        # Load check icon image for installed items with missing info, resize to 34x16 px
        self.check_caution_image = ImageTk.PhotoImage(Image.open("data/assets/check_caution.png").resize((34, 16)))

        # Main frame to hold the UI components with themed background
        self.main_frame = Frame(master, bg=self.theme.get("background", "#2e2e2e"))
        self.main_frame.pack(fill=BOTH, expand=True)

        # Left frame for the Treeview listing zip packages
        self.left_frame = Frame(self.main_frame, bg=self.theme.get("background", "#2e2e2e"))
        self.left_frame.pack(side="left", fill=BOTH, expand=False, padx=5, pady=5)

        # Mod name
        self.mod_name_label = Label(self.left_frame, textvariable=self.mod_name, font=("Arial", 18, "bold"), bg=self.theme.get("background", "#2e2e2e"), fg=self.theme.get("foreground", "white"))
        self.mod_name_label.pack(anchor="w")

        # Container frame for treeview and its scrollbar
        self.tree_container = Frame(self.left_frame, bg=self.theme.get("background", "#2e2e2e"))
        self.tree_container.pack(fill=BOTH, expand=True)  # Fill vertically and horizontally as needed

        # Vertical scrollbar on the right side of the treeview container
        self.scrollbar = Scrollbar(self.tree_container)
        self.scrollbar.pack(side=RIGHT, fill=Y)

        # Treeview widget to show the zip packages as a simple tree list (no columns)
        self.tree = ttk.Treeview(self.tree_container, show='tree')
        self.tree.pack(side="left", fill=BOTH, expand=True)

        # Connect scrollbar and treeview vertical scrolling
        self.tree.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.tree.yview)

        # Populate treeview with zip data
        for i, item in enumerate(self.zip_data):
            if not item.get("files"):
                icon = self.error_image
            else:
                is_installed = self.is_installed(item)
                missing_preview = not os.path.exists(item.get("preview", ""))
                missing_chunk_id = not item.get("chunk_id")
                missing_replaces = not item.get("replaces")
                missing_description = not item.get("description")
                has_warnings = missing_preview or missing_chunk_id or missing_replaces or missing_description

                if is_installed and has_warnings:
                    icon = self.check_caution_image
                elif is_installed:
                    icon = self.check_image
                elif has_warnings:
                    icon = self.caution_image
                else:
                    icon = ""

            padded_title = "   " + item["title"]
            self.tree.insert("", "end", iid=str(i), text=padded_title, image=icon)

        # Auto-resize the treeview column width based on content width
        self.auto_resize_tree_column()
        self.update_tree_scrollbar_visibility()

        # Right frame to hold preview canvas for selected zip package
        self.right_frame = Frame(self.main_frame, bg=self.theme.get("background", "#2e2e2e"))
        self.right_frame.pack(side="right", fill=BOTH, expand=True, padx=5, pady=5)

        # Canvas widget to display preview image of selected zip package
        self.preview_canvas = Canvas(self.right_frame, bg=self.theme.get("background", "#2e2e2e"), highlightthickness=0)
        self.preview_canvas.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Bind resizing event on canvas to adjust preview image size dynamically
        self.preview_canvas.bind("<Configure>", self.resize_preview_image)

        # Frame below the preview canvas to hold the mod details
        self.details_frame = Frame(self.right_frame, bg=self.theme.get("background", "#2e2e2e"))
        self.details_frame.pack(fill="x", padx=10, pady=(0, 10))  # Padding bottom only

        # Label or text variable to hold the detail info
        self.details_text = StringVar()
        self.details_label = ttk.Label(
            self.details_frame,
            textvariable=self.details_text,
            wraplength=400,
            justify="left",
            background=self.theme.get("background", "#2e2e2e"),
            foreground=self.theme.get("foreground", "white")
        )
        self.details_label.pack(anchor="w")

        # Frame to hold buttons at the bottom
        button_frame = Frame(master, bg=self.theme.get("background", "#2e2e2e"))
        button_frame.pack(pady=(10, 10))

        # Install/uninstall button triggers install_or_uninstall method
        self.install_button = ttk.Button(button_frame, text="Install", command=self.install_or_uninstall)
        self.install_button.pack(side="left", padx=5)

        # Button to set installation directory
        self.set_dir_button = ttk.Button(button_frame, text="Set Install Directory", command=self.set_install_dir)
        self.set_dir_button.pack(side="left", padx=5)
        install_dir = self.get_install_dir()
        if install_dir:
            self.set_dir_button = WidgetToolTip(self.set_dir_button, install_dir, theme=self.theme)

        # Frame to hold buttons at the bottom
        self.button_frame = Frame(master, bg=self.theme.get("background", "#2e2e2e"))
        self.button_frame.pack(pady=(10, 10))

        # Path to the external Mod Option Builder executable
        mod_builder_exe = "Mod_Option_Builder.exe"

        # Function to launch the external program
        def open_mod_option_builder():
            try:
                subprocess.Popen([mod_builder_exe], shell=True)
            except Exception as e:
                messagebox.showerror("Error", f"Could not launch Mod Option Builder:\n{e}")

        # Add button if the executable exists
        if os.path.exists(mod_builder_exe):
            self.builder_button = ttk.Button(button_frame, text="Open Mod Option Builder", command=open_mod_option_builder)
            self.builder_button.pack(side="left", padx=5)

        # Button to open settings window
        self.settings_button = ttk.Button(button_frame, text="Settings", command=self.open_settings_window)
        self.settings_button.pack(side="left", padx=5)

        self.about_button = ttk.Button(button_frame, text="About", command=self.open_about_window)
        self.about_button.pack(side="left", padx=5)

        # Button to exit application with confirmation
        self.exit_button = ttk.Button(button_frame, text="Exit", command=self.confirm_exit)
        self.exit_button.pack(side="left", padx=5)

        # Store the original PIL Image for the preview (used for resizing)
        self.current_preview_image = None

        # Bind treeview selection event to show preview of selected zip
        self.tree.bind("<<TreeviewSelect>>", self.show_preview)

        # Select first item by default and show its preview
        if self.tree.get_children():
            first_id = self.tree.get_children()[0]
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self.tree.see(first_id)
            self.show_preview(None)
        
        self.tree_tooltip = TreeviewToolTip(self.tree, theme=self.theme)
        self.last_tree_item = None  # Track last hovered item
        self.tree.bind("<Motion>", self.on_tree_hover)

    def update_tree_scrollbar_visibility(self):
        self.tree.update_idletasks()  # Ensure layout is updated

        needs_scrollbar = self.tree.yview() != (0.0, 1.0)
        if needs_scrollbar:
            self.scrollbar.pack(side="right", fill="y")
        else:
            self.scrollbar.pack_forget()

    def get_install_dir(self):
        """
        Returns the current raw install directory as a string,
        or an empty string if not set.
        """
        return self.settings.get("install_dir", "")

    def check_mod_options_data_changes(self):
        try:
            current_mtime = os.path.getmtime(OPTIONS_FILE)
            if current_mtime != self.last_zip_data_mtime:
                print("Detected change in mod_options.json, refreshing...")
                self.last_zip_data_mtime = current_mtime
                self.reload_zip_data()
        except Exception as e:
            print(f"Error checking mod_options.json: {e}")

        self.master.after(2000, self.check_mod_options_data_changes)  # Repeat every 2 seconds

    def reload_zip_data(self):
        self.load_zip_data()

        # Clear Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Re-populate Treeview
        for i, item in enumerate(self.zip_data):
            if not item.get("files"):
                icon = self.error_image
            else:
                is_installed = self.is_installed(item)
                missing_preview = not os.path.exists(item.get("preview", ""))
                missing_chunk_id = not item.get("chunk_id")
                missing_replaces = not item.get("replaces")
                missing_description = not item.get("description")
                has_warnings = missing_preview or missing_chunk_id or missing_replaces or missing_description

                if is_installed and has_warnings:
                    icon = self.check_caution_image
                elif is_installed:
                    icon = self.check_image
                elif has_warnings:
                    icon = self.caution_image
                else:
                    icon = ""

            padded_title = "   " + item["title"]
            self.tree.insert("", "end", iid=str(i), text=padded_title, image=icon)

        self.auto_resize_tree_column()
        self.update_tree_scrollbar_visibility()

        # Reselect first item (optional)
        if self.tree.get_children():
            first_id = self.tree.get_children()[0]
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self.tree.see(first_id)
            self.show_preview(None)

    def auto_resize_tree_column(self):
        """
        Adjust the width of the treeview's single column based on the widest item text,
        plus some padding for icons and spacing.
        """
        padding = 40  # extra space for icon/padding

        style = ttk.Style()
        tree_font_name = style.lookup("Treeview", "font")  # Get treeview font name
        tree_font = font.nametofont(tree_font_name)        # Get font object for measuring text width

        max_text_width = 0

        # Find the widest text among all tree items
        for item_id in self.tree.get_children():
            text = self.tree.item(item_id, "text")
            text_width = tree_font.measure(text)
            max_text_width = max(max_text_width, text_width)

        # Set column width to max width + padding or minimum 200 px
        new_width = max(200, max_text_width + padding)
        self.tree.column("#0", width=new_width)

    def confirm_exit(self):
        """
        Confirm exit dialog if configured in settings. Quits the main loop if confirmed or no prompt set.
        """
        if self.settings.get("PromptBeforeExit", False):
            answer = messagebox.askyesno(self.app_name, "Are you sure you want to exit?")
            if not answer:
                return
        self.master.quit()

    def load_theme(self):
        """
        Load theme JSON file if it exists, otherwise default to empty dict.
        If file is corrupted, print error and load empty theme.
        """
        if os.path.exists(THEME_FILE):
            try:
                with open(THEME_FILE, 'r') as f:
                    self.theme = json.load(f)
            except json.JSONDecodeError:
                print("Invalid theme.json. Using defaults...")
                self.theme = {}
        else:
            self.theme = {}

    def set_theme_style(self):
        """
        Setup ttk widget style configurations according to loaded theme colors.
        This includes Treeview layout, buttons, and custom checkbuttons.
        """
        style = ttk.Style()
        style.theme_use("default")  # Use default ttk theme as base

        # Customize Treeview item layout to show image on left and text stretched
        style.layout("Treeview.Item", [
            ("Treeitem.padding", {
                "sticky": "nswe",
                "children": [
                    ("Treeitem.image", {"side": "left", "sticky": ""}),
                    ("Treeitem.text", {"sticky": "nswe"})
                ]
            })
        ])

        # Basic button layout (border and padding)
        style.layout("TButton", [
            ("Button.border", {"sticky": "nswe", "children": [
                ("Button.padding", {"sticky": "nswe", "children": [
                    ("Button.label", {"sticky": "nswe"})
                ]})
            ]})
        ])

        # Custom checkbutton layout: indicator left, label stretched
        style.layout("Custom.TCheckbutton", [
            ("Checkbutton.padding", {"sticky": "nswe", "children": [
                ("Checkbutton.indicator", {"side": "left", "sticky": ""}),
                ("Checkbutton.label", {"sticky": "nswe"})
            ]})
        ])

        # Configure colors and padding for custom checkbutton using theme
        style.configure("Custom.TCheckbutton",
                background=self.theme.get("background", "#2e2e2e"),
                foreground=self.theme.get("foreground", "white"),
                padding=5)

        # Change checkbutton colors when active or pressed
        style.map("Custom.TCheckbutton",
                background=[("active", self.theme.get("button_active_bg", "#666")),
                            ("pressed", self.theme.get("button_active_bg", "#555"))],
                foreground=[("active", self.theme.get("button_fg", "white")),
                            ("pressed", self.theme.get("button_fg", "white"))])

        # Configure regular button colors and padding
        style.configure("TButton", 
                        background=self.theme.get("button_bg", "#444"), 
                        foreground=self.theme.get("button_fg", "white"), 
                        borderwidth=0, padding=6)
        style.map("TButton", background=[("active", self.theme.get("button_active_bg", "#666"))])

        # Configure label colors according to theme
        style.configure("TLabel", 
                        background=self.theme.get("background", "#2e2e2e"), 
                        foreground=self.theme.get("foreground", "white"))

        # Configure Treeview colors (background, foreground, selection)
        style.configure("Treeview",
                        background=self.theme.get("background", "#2e2e2e"),
                        foreground=self.theme.get("foreground", "white"),
                        fieldbackground=self.theme.get("background", "#2e2e2e"))
        style.map("Treeview", background=[("selected", self.theme.get("select_bg", "#444"))])

    def load_settings(self):
        """
        Load settings JSON file, set defaults if missing or invalid.
        """
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    content = f.read().strip()
                    # Load JSON if not empty
                    self.settings = json.loads(content) if content else {}
            except json.JSONDecodeError:
                print("Invalid settings.json. Resetting...")
                self.settings = {}
        else:
            self.settings = {}

        # Default settings if not present
        self.settings.setdefault("CanInstallMultiple", False)
        self.settings.setdefault("PromptUser", False)
        self.settings.setdefault("PromptBeforeExit", False)

    def save_settings(self):
        """
        Save current settings to settings JSON file.
        """
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def load_zip_data(self):
        """
        Load zip package metadata from JSON file.
        """
        with open(OPTIONS_FILE, 'r') as f:
            data = json.load(f)

        self.mod_name = StringVar()
        self.mod_name.set(data.get("mod_name", "Unknown Mod"))

        self.zip_data = data.get("entries", [])

    def show_preview(self, event):
        """
        Show preview image of the currently selected zip item.
        """
        selected_id = self.tree.focus()
        if not selected_id:
            return

        index = int(selected_id)
        preview_path = self.zip_data[index]["preview"]

        try:
            # Open preview image and store original for resizing
            image = Image.open(preview_path)
            self.current_preview_image = image
            self.resize_preview_image()
        except Exception as e:
            # On failure, clear preview and reset image reference
            print(f"Error loading preview image: {e}")
            self.preview_canvas.delete("all")
            self.current_preview_image = None

        # Populate the details box
        # Populate the details box, including the mod name
        mod_title = self.zip_data[index].get("title", "Unknown Title")
        chunk_id = self.zip_data[index].get("chunk_id", "N/A")
        replaces = self.zip_data[index].get("replaces", "N/A")
        description = self.zip_data[index].get("description", "No description provided.")

        details_string = (
            f"Mod: {mod_title}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Replaces: {replaces}\n"
            f"Description: {description}"
        )

        self.details_text.set(details_string)

        # Update install/uninstall button text based on current selection
        self.update_install_button()

    def resize_preview_image(self, event=None):
        """
        Resize preview image to fit inside the preview canvas while maintaining aspect ratio.
        """
        if not self.current_preview_image:
            return

        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        # Avoid resizing too early when widget not fully initialized
        if canvas_width < 10 or canvas_height < 10:
            return

        img = self.current_preview_image
        img_ratio = img.width / img.height
        canvas_ratio = canvas_width / canvas_height

        # Calculate new size preserving aspect ratio
        if img_ratio > canvas_ratio:
            new_width = canvas_width
            new_height = int(canvas_width / img_ratio)
        else:
            new_height = canvas_height
            new_width = int(canvas_height * img_ratio)

        # Resize image using high-quality resampling filter
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(resized)

        # Clear canvas and draw resized image centered
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor="center")

        # Keep reference to PhotoImage to prevent garbage collection
        self.preview_canvas.image = photo

    def set_install_dir(self):
        """
        Open a dialog for user to select installation directory and save it to settings.
        """
        directory = filedialog.askdirectory(title="Select Installation Directory")
        if directory:
            self.settings["install_dir"] = directory
            self.save_settings()
            # Update UI and buttons to reflect new install directory
            self.update_install_button()
            self.refresh_tree_icons()

    def update_install_button(self):
        """
        Update install/uninstall button text depending on whether
        the selected zip is currently installed.
        """
        selected_id = self.tree.focus()
        if not selected_id:
            self.install_button.config(text="Install")
            return

        index = int(selected_id)
        selected = self.zip_data[index]
        install_dir = self.settings.get("install_dir")

        # If no install dir or no files listed, default button text
        if not install_dir or not selected.get("files"):
            self.install_button.config(text="Install")
            return

        # Check if all files for this zip exist in install directory
        all_exist = all(os.path.exists(os.path.join(install_dir, f)) for f in selected["files"])
        # Set button text accordingly
        self.install_button.config(text="Uninstall" if all_exist else "Install")

    def uninstall_files(self, files):
        """
        Remove given list of files from the installation directory.
        """
        install_dir = self.settings.get("install_dir")
        for f in files:
            path = os.path.join(install_dir, f)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Could not remove {path}: {e}")

    def uninstall_other_zips(self, current_index):
        """
        Uninstall all other installed zip packages except the one at current_index.
        """
        install_dir = self.settings.get("install_dir")
        for i, item in enumerate(self.zip_data):
            if i == current_index:
                continue
            if "files" in item:
                for f in item["files"]:
                    path = os.path.join(install_dir, f)
                    if os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            print(f"Could not remove {path}: {e}")

    def install_or_uninstall(self):
        """
        Triggered when user clicks install/uninstall button.
        Installs or uninstalls the selected zip package accordingly,
        handling prompts and multiple install settings.
        """
        selected_id = self.tree.focus()
        if not selected_id:
            return
        selected_index = int(selected_id)
        selected = self.zip_data[selected_index]
        install_dir = self.settings.get("install_dir")

        # If no install directory, prompt user to set it first
        if not install_dir:
            self.set_install_dir()
            install_dir = self.settings.get("install_dir")
            if not install_dir:
                return  # User cancelled

        # Check if zip is currently installed (all files present)
        is_installed = all(os.path.exists(os.path.join(install_dir, f)) for f in selected.get("files", []))

        if is_installed:
            # If installed, confirm uninstall if prompt enabled
            if self.settings.get("PromptUser", False):
                answer = messagebox.askyesno(f"{self.app_name} - Confirm Uninstall", f"Do you want to uninstall '{selected['title']}'?")
                if not answer:
                    return
            # Uninstall files and update button
            self.uninstall_files(selected["files"])
            self.install_button.config(text="Install")
        else:
            # If not installed, handle multiple installs setting
            if not self.settings.get("CanInstallMultiple", False):
                other_installed = False
                for i, item in enumerate(self.zip_data):
                    if i == selected_index:
                        continue
                    if "files" in item:
                        # Check if other zip is installed
                        if all(os.path.exists(os.path.join(install_dir, f)) for f in item["files"]):
                            other_installed = True
                            break
                # Prompt user if another zip is installed and prompts enabled
                if other_installed and self.settings.get("PromptUser", False):
                    answer = messagebox.askyesno(f"{self.app_name} - Confirm Replace",
                        f"Another option is already installed.\nDo you want to uninstall it and install '{selected['title']}'?")
                    if not answer:
                        return

            # Uninstall other zips if multiple installs not allowed
            if not self.settings.get("CanInstallMultiple", False):
                self.uninstall_other_zips(selected_index)

            # Extract selected zip package to install directory
            zip_path = selected["zip_path"]
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(install_dir)

            self.install_button.config(text="Uninstall")

        # Refresh the treeview icons to show updated install status
        self.refresh_tree_icons()

    def is_installed(self, item):
        """
        Check if all files listed in the item exist in the install directory.
        Returns True if installed, False otherwise.
        """
        install_dir = self.settings.get("install_dir")
        return all(os.path.exists(os.path.join(install_dir, f)) for f in item.get("files", [])) if install_dir else False

    def refresh_tree_icons(self):
        """
        Refresh the icons in the treeview based on installed status
        or missing file metadata.
        """
        for i, item in enumerate(self.zip_data):
            if not item.get("files"):
                icon = self.error_image
            else:
                is_installed = self.is_installed(item)
                missing_preview = not os.path.exists(item.get("preview", ""))
                missing_chunk_id = not item.get("chunk_id")
                missing_replaces = not item.get("replaces")
                missing_description = not item.get("description")
                has_warnings = missing_preview or missing_chunk_id or missing_replaces or missing_description

                if is_installed and has_warnings:
                    icon = self.check_caution_image
                elif is_installed:
                    icon = self.check_image
                elif has_warnings:
                    icon = self.caution_image
                else:
                    icon = ""

            self.tree.item(str(i), image=icon)

    def on_tree_hover(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "tree":
            self.tree_tooltip.hide_tip()
            self.last_tree_item = None
            return

        item_id = self.tree.identify_row(event.y)
        if not item_id:
            self.tree_tooltip.hide_tip()
            self.last_tree_item = None
            return

        if item_id == self.last_tree_item:
            return  # same item, do nothing

        self.last_tree_item = item_id
        index = int(item_id)
        item = self.zip_data[index]

        # Tooltip content
        if not item.get("files"):
            tooltip_text = "Error: No files were listed..."
        else:
            warnings = []
            if not os.path.exists(item.get("preview", "")):
                warnings.append("Missing preview image")
            if not item.get("chunk_id"):
                warnings.append("Missing chunk ID")
            if not item.get("replaces"):
                warnings.append("Missing 'replaces' field")
            if not item.get("description"):
                warnings.append("Missing description")

            tooltip_lines = []

            if self.is_installed(item):
                tooltip_lines.append("Installed")

            if warnings:
                tooltip_lines.append("Caution:")
                tooltip_lines.extend(warnings)

            tooltip_text = "\n".join(tooltip_lines)

        if tooltip_text:
            self.tree_tooltip.show_tip(tooltip_text, event.x_root + 20, event.y_root - 30)
        else:
            self.tree_tooltip.hide_tip()

    def open_settings_window(self):
        """
        Open a modal settings window allowing the user to change install directory
        and toggle some boolean settings with checkboxes.
        """
        win = Toplevel(self.master)
        win.title("Settings")

        # Colors from theme for styling
        fg = self.theme.get("foreground", "white")
        bg = self.theme.get("background", "#2e2e2e")
        win.configure(bg=bg)
        win.resizable(False, False)

        # Function to center the settings window on screen
        def center_window():
            win.update_idletasks()
            width = win.winfo_width()
            height = win.winfo_height()
            screen_width = win.winfo_screenwidth()
            screen_height = win.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            win.geometry(f"{width}x{height}+{x}+{y}")

        win.after(0, center_window)

        # Helper function to shorten long paths for display
        def short_path(path, max_len=35):
            return path if len(path) <= max_len else "..." + path[-max_len:]

        # Label for install directory
        ttk.Label(win, text="Install Directory:", background=bg, foreground=fg).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 2)
        )

        # Display current install directory or placeholder text
        install_dir_raw = self.settings.get("install_dir") or ""
        install_dir_display = short_path(install_dir_raw) if install_dir_raw else "No install directory set"
        install_dir_var = StringVar(value=install_dir_display)

        install_dir_label = ttk.Label(win, textvariable=install_dir_var, background=bg, foreground=fg)
        install_dir_label.grid(row=1, column=0, sticky="w", padx=10)
        install_dir_tooltip = WidgetToolTip(install_dir_label, install_dir_raw if install_dir_raw else "No install directory set", theme=self.theme)

        # Button to change installation directory
        def change_dir():
            initial_dir = self.settings.get("install_dir", None)
            directory = filedialog.askdirectory(title="Select Installation Directory", parent=win, initialdir=initial_dir)
            if directory:
                self.settings["install_dir"] = directory
                self.save_settings()
                install_dir_var.set(short_path(directory))
                install_dir_tooltip.text = directory
            # Update main UI after directory change
            self.update_install_button()
            self.refresh_tree_icons()
            win.update_idletasks()
            win.geometry("")  # Reset window size to fit content

        change_dir_btn = ttk.Button(win, text="Change Directory", command=change_dir)
        change_dir_btn.grid(row=1, column=1, padx=10, pady=5)
        WidgetToolTip(change_dir_btn, "Choose the folder where mods will be installed.", theme=self.theme)

        # BooleanVars bound to checkbox widgets for settings toggles
        can_multi = BooleanVar(value=self.settings.get("CanInstallMultiple", False))
        prompt_user = BooleanVar(value=self.settings.get("PromptUser", False))
        prompt_exit = BooleanVar(value=self.settings.get("PromptBeforeExit", False))

        # Checkbox to allow multiple simultaneous installs
        chk_multi = ttk.Checkbutton(
            win,
            text="Allow Multiple Installs",
            variable=can_multi,
            style="Custom.TCheckbutton"
        )
        chk_multi.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 2))
        WidgetToolTip(chk_multi, "Allows more than one mod to be installed at the same time.\n\n(Not recommended for mods with different styles that replace the same thing)", theme=self.theme)

        # Checkbox to prompt before replacing/uninstalling
        chk_prompt_replace = ttk.Checkbutton(
            win,
            text="Prompt Before Replace/Uninstall",
            variable=prompt_user,
            style="Custom.TCheckbutton"
        )
        chk_prompt_replace.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 2))
        WidgetToolTip(chk_prompt_replace, "Ask for confirmation before replacing or uninstalling mods.", theme=self.theme)

        # Checkbox to prompt before exiting app
        chk_prompt_exit = ttk.Checkbutton(
            win,
            text="Prompt Before Exit",
            variable=prompt_exit,
            style="Custom.TCheckbutton"
        )
        chk_prompt_exit.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 2))
        WidgetToolTip(chk_prompt_exit, "Ask for confirmation before closing the application.", theme=self.theme)

        # OK button to save settings and close window
        def save_and_close():
            self.settings["CanInstallMultiple"] = can_multi.get()
            self.settings["PromptUser"] = prompt_user.get()
            self.settings["PromptBeforeExit"] = prompt_exit.get()
            self.save_settings()
            win.destroy()

        ttk.Button(win, text="OK", command=save_and_close).grid(row=5, column=0, columnspan=2, pady=10)

        # Final setup for modal behavior and appearance
        win.update_idletasks()
        win.geometry("")
        win.transient(self.master)       # Keep on top of main window
        win.iconbitmap("data/assets/settings.ico")  # Window icon
        win.grab_set()                   # Make modal
        self.master.wait_window(win)     # Wait until settings window closed

    def open_about_window(self):
        about_win = Toplevel(self.master)
        about_win.title("About")
        about_win.configure(bg=self.theme.get("background", "#2e2e2e"))
        about_win.resizable(False, False)

        fg = self.theme.get("foreground", "white")
        bg = self.theme.get("background", "#2e2e2e")

        # --- Hardcoded Info ---
        program_name = self.app_name
        version = self.app_version
        author = self.app_author
        author_link = self.app_author_weblink
        github_link = self.app_github_weblink
        # ------------------------

        ttk.Label(about_win, text=program_name, font=("Arial", 14, "bold"), background=bg, foreground=fg).pack(padx=20, pady=(15, 5))
        ttk.Label(about_win, text=f"Version: {version}", background=bg, foreground=fg).pack(pady=2)
        ttk.Label(about_win, text=f"Author: {author}", background=bg, foreground=fg).pack(pady=2)

        def open_link(event):
            import webbrowser
            webbrowser.open_new_tab(author_link)

        link_label = ttk.Label(about_win, text=author_link, foreground="skyblue", cursor="hand2", background=bg)
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", open_link)

        link_label2 = ttk.Label(about_win, text=github_link, foreground="skyblue", cursor="hand2", background=bg)
        link_label2.pack(pady=5)
        link_label2.bind("<Button-1>", open_link)

        ttk.Button(about_win, text="OK", command=about_win.destroy).pack(pady=(10, 15))

        # Center the window on screen
        def center_window():
            about_win.update_idletasks()
            width = about_win.winfo_width()
            height = about_win.winfo_height()
            screen_width = about_win.winfo_screenwidth()
            screen_height = about_win.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            about_win.geometry(f"{width}x{height}+{x}+{y}")

        about_win.after(0, center_window)  # Schedule after first draw

        # Modal behavior
        about_win.iconbitmap("data/assets/icon.ico")
        about_win.transient(self.master)
        about_win.grab_set()
        self.master.wait_window(about_win)

class WidgetToolTip:
    def __init__(self, widget, text, theme=None):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.theme = theme or {}
        self.bg = self.theme.get("tooltip_bg", "#2e2e2e")
        self.fg = self.theme.get("tooltip_fg", "white")

        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)
        self.widget.bind("<Motion>", self.move_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return

        self.tip_window = Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.attributes("-topmost", True)

        label = ttk.Label(
            self.tip_window,
            text=self.text,
            background=self.bg,
            foreground=self.fg,
            relief="solid",
            borderwidth=1,
            padding=5
        )
        label.pack()
        self.move_tip(event)

    def move_tip(self, event):
        if self.tip_window:
            x = event.x_root + 20
            y = event.y_root - 30
            self.tip_window.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class TreeviewToolTip:
    def __init__(self, widget, theme=None):
        self.widget = widget
        self.tip_window = None
        self.theme = theme or {}
        self.bg = self.theme.get("tooltip_bg", "#2e2e2e")
        self.fg = self.theme.get("tooltip_fg", "white")

    def show_tip(self, text, x, y):
        self.hide_tip()  # Close any existing tooltip
        if not text:
            return

        self.tip_window = Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.attributes("-topmost", True)
        self.tip_window.geometry(f"+{x}+{y}")

        label = ttk.Label(
            self.tip_window,
            text=text,
            background=self.bg,
            foreground=self.fg,
            relief="solid",
            borderwidth=1,
            padding=5
        )
        label.pack()

    def hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

if __name__ == "__main__":
    # Initialize Tkinter root window
    root = Tk()
    root.iconbitmap("data/assets/icon.ico")  # Set main app window icon

    root.minsize(950, 600)  # Set minimum window size

    # Create and run the app instance
    app = ModOptionSelectorApp(root)
    root.mainloop()

# After app exits, unlock and remove the lock file to allow future runs
try:
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    lock_file.close()
    os.remove(lock_file_path)
except Exception:
    # Silently ignore any errors during cleanup
    pass