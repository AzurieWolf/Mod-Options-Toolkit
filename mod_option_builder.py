# Import required standard and third-party modules
import json
import os
import zipfile
import shutil
import subprocess
import platform
import sys             # To exit the program on errors
import tempfile        # To get temp directory for lock file
import msvcrt          # For Windows file locking (prevent multiple instances)
import tkinter as tk
from tkinter import (  # GUI components from tkinter
    Tk, ttk, Frame, Label, Entry, Button, Listbox, Scrollbar, END, SINGLE,
    filedialog, messagebox, StringVar, Toplevel, Canvas, Text
)
from PIL import Image, ImageTk  # For handling and displaying image previews

# Define a lock file path in temp directory to prevent multiple app instances
lock_file_path = os.path.join(tempfile.gettempdir(), "mod_options_builder.lock")

try:
    # Try to create and lock the file exclusively
    lock_file = open(lock_file_path, "w")
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    # If lock fails, app is already running, so show error and quit
    messagebox.showerror("Already Running", "The application is already running.")
    sys.exit()

# Constants for file paths
JSON_FILE = "data/mod_options.json"
DEFAULT_IMAGE = "data/assets/options_builder/default.png"

# Main GUI application class
class JsonBuilderApp:
    def __init__(self, master):
        self.root = master
        self.master = master

        # App display name and version
        self.app_name = "Mod Option Builder"
        self.app_version = "1.0.1"
        self.app_author = "AzurieWolf"

        # Set window title with app name and version
        master.title(self.app_name + " v" + self.app_version + " by " + self.app_author)
        
        master.minsize(900, 500)

        # Initialize data
        self.data = []  # Holds the list of entries
        self.current_index = None  # Current selected entry index
        self.current_image = None  # Holds current image preview

        # === LEFT SIDE === #
        # Frame for entry list
        left_frame = Frame(master)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        # Build a frame to hold buttons
        btn_frame = Frame(left_frame)
        btn_frame.pack(fill="x", pady=2)

        # Save button
        self.save_button = Button(btn_frame, text="Save", command=self.save_all)
        self.save_button.pack(side="left", padx=2)
        ToolTip(self.save_button, "Save all changes (Copies selected zip files and preview images to the data/zips folder)")

        # Pack button
        self.pack_button = Button(btn_frame, text="Pack Mod", command=self.create_mod_zip)
        self.pack_button.pack(side="left", padx=2)
        ToolTip(self.pack_button, "Create a zip file containing the mod files and mod option selector.")

        Label(left_frame, text="Mod Name:").pack(anchor="w", padx=2)
        self.mod_name_var = StringVar()
        self.mod_name_entry = Entry(left_frame, textvariable=self.mod_name_var)
        self.mod_name_entry.pack(fill="x", padx=2, pady=(0, 5))
        self.mod_name_var.trace_add("write", lambda *args: self.mark_dirty())

        # Buttons to add/delete and move up and move down entries
        Button(btn_frame, text="Add Entry", command=self.add_entry).pack(side="left", padx=0)
        Button(btn_frame, text="Delete Entry", command=self.delete_entry).pack(side="left", padx=2)
        # Move up button
        self.move_up_button = Button(btn_frame, text="↑", command=self.move_entry_up)
        self.move_up_button.pack(side="left", padx=2)
        ToolTip(self.move_up_button, "Move selected entry up")

        # Move down button
        self.move_down_button = Button(btn_frame, text="↓", command=self.move_entry_down)
        self.move_down_button.pack(side="left", padx=2)
        ToolTip(self.move_down_button, "Move selected entry down")

        Label(left_frame, text="Entries").pack()

        # Frame to hold listbox and scrollbar
        listbox_frame = Frame(left_frame)
        listbox_frame.pack(fill="both", expand=True)

        # Listbox to display entry titles
        self.entry_listbox = Listbox(listbox_frame, width=40, height=20, selectmode=SINGLE, exportselection=False)
        self.entry_listbox.pack(side="left", fill="both", expand=True)

        # Scrollbar for listbox
        scrollbar = Scrollbar(listbox_frame, command=self.entry_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.entry_listbox.config(yscrollcommand=scrollbar.set)

        # Bind listbox selection event
        self.entry_listbox.bind("<<ListboxSelect>>", self.on_entry_select)

        # === RIGHT SIDE === #
        right_frame = Frame(master)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Grid configuration
        right_frame.columnconfigure(1, weight=1)  # Make title entry expand
        right_frame.columnconfigure(3, weight=0)  # Keep image preview fixed

        # Title field
        Label(right_frame, text="Title:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.title_var = StringVar()
        self.title_entry = Entry(right_frame, textvariable=self.title_var)
        self.title_entry.grid(row=0, column=1, sticky="ew", pady=2, columnspan=2, padx=(0, 10))

        # Image preview canvas
        self.canvas = Canvas(right_frame, width=200, height=200, bg="white", bd=1, relief="solid")
        self.canvas.grid(row=0, column=3, rowspan=4, padx=5, pady=5)

        self.zip_manually_selected = False
        self.preview_manually_selected = False

        # ZIP file selection
        Label(right_frame, text="ZIP File:").grid(row=1, column=0, sticky="w", padx=5)
        self.zip_combo = ttk.Combobox(right_frame, state="readonly")
        self.zip_combo.grid(row=1, column=1, sticky="ew", pady=2)
        self.zip_combo.bind("<<ComboboxSelected>>", self.zip_selected)
        Button(right_frame, text="Browse...", command=self.browse_zip).grid(row=1, column=2, sticky="w", padx=5)

        # Preview image selection
        Label(right_frame, text="Preview Image:").grid(row=2, column=0, sticky="w", padx=5)
        self.preview_combo = ttk.Combobox(right_frame, state="readonly")
        self.preview_combo.grid(row=2, column=1, sticky="ew", pady=2)
        self.preview_combo.bind("<<ComboboxSelected>>", self.preview_selected)
        Button(right_frame, text="Browse...", command=self.browse_preview).grid(row=2, column=2, sticky="w", padx=5)

        # Listbox for files inside ZIP
        Label(right_frame, text="Files:").grid(row=3, column=0, sticky="nw", pady=5, padx=5)
        self.files_listbox = Listbox(right_frame, width=50, height=6)
        self.files_listbox.grid(row=3, column=1, sticky="ew", pady=5, columnspan=2)

        # Add/Delete file buttons
        self.files_listbox.bind("<<ListboxSelect>>", self.on_file_select)
        files_btn_frame = Frame(right_frame)
        files_btn_frame.grid(row=4, column=1, sticky="w", padx=0)
        Button(files_btn_frame, text="Add File", command=self.add_file).pack(side="left", padx=0)
        self.deleteFileButton = Button(files_btn_frame, text="Delete File", state="disabled", command=self.delete_file)
        self.deleteFileButton.pack(side="left", padx=2)
        self.deleteFileButton.config(state="disabled")

        self.getFilesButton = Button(files_btn_frame, text="Get Files", command=self.get_files_from_zip)
        self.getFilesButton.pack(side="left", padx=2)
        ToolTip(self.getFilesButton, "Reload files from the selected ZIP archive")

        self.title_var.trace_add("write", lambda *args: self.mark_dirty())
        self.zip_combo.bind("<<ComboboxSelected>>", lambda e: (self.zip_selected(e), self.mark_dirty()))
        self.preview_combo.bind("<<ComboboxSelected>>", lambda e: (self.preview_selected(e), self.mark_dirty()))

        self.is_dirty = False
        self.loading_entry = False

        # Spacer
        Label(right_frame, text="", height=1).grid(row=5, column=1)

        # Mod Details
        # Chunk ID
        Label(right_frame, text="Chunk ID:").grid(row=6, column=0, sticky="w", padx=5)
        self.chunk_id_var = StringVar()
        self.chunk_id_entry = Entry(right_frame, textvariable=self.chunk_id_var)
        self.chunk_id_entry.grid(row=6, column=1, sticky="ew", padx=(0, 10))
        self.chunk_id_var.trace_add("write", lambda *args: self.mark_dirty())

        # Replaces
        Label(right_frame, text="Replaces:").grid(row=7, column=0, sticky="w", padx=5)
        self.replaces_var = StringVar()
        self.replaces_entry = Entry(right_frame, textvariable=self.replaces_var)
        self.replaces_entry.grid(row=7, column=1, sticky="ew", padx=(0, 10))
        self.replaces_var.trace_add("write", lambda *args: self.mark_dirty())

        # Description
        Label(right_frame, text="Description:").grid(row=8, column=0, sticky="w", padx=5)
        self.description_entry = Text(right_frame, height=7, wrap="word", undo=True)
        self.description_entry.grid(row=8, column=1, sticky="ew", padx=(0, 10))
        self.description_entry.bind("<KeyRelease>", lambda event: self.mark_dirty())

        # Populate dropdowns and load data
        self.populate_zip_files()
        self.populate_preview_images()
        self.load_json()

    def mark_dirty(self, event=None):
        if self.loading_entry:
            print("Skipped mark_dirty: loading_entry is True")
            return
        if not self.is_dirty:
            print("Marking dirty")
            self.is_dirty = True
            self.save_button.config(text="Save*")
            self.save_button.config(state="normal")

    def on_form_change(self, *args):
        if self.loading_entry:
            return
        self.mark_dirty()

    def select_zip_file(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if path:
            self._manual_zip_path = path
            self.zip_combo.set(os.path.basename(path))  # Set dropdown display
            self.zip_manually_selected = True

    def select_preview_file(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if path:
            self._manual_preview_path = path
            self.preview_combo.set(os.path.basename(path))
            self.preview_manually_selected = True

    # Populate the ZIP file dropdown
    def populate_zip_files(self):
        folder = "data/zips"
        os.makedirs(folder, exist_ok=True)
        self.zip_combo['values'] = [f for f in os.listdir(folder) if f.endswith(".zip")]

    # Populate the preview image dropdown
    def populate_preview_images(self):
        folder = "data/zips/previews"
        os.makedirs(folder, exist_ok=True)
        previews = ["None"] + [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        self.preview_combo['values'] = previews

    # When ZIP file selected, extract and display file list
    def zip_selected(self, event):
        selected_zip = self.zip_combo.get()
        path = os.path.join("data/zips", selected_zip)
        try:
            with zipfile.ZipFile(path, 'r') as zip_ref:
                file_names = zip_ref.namelist()
            self.files_listbox.delete(0, END)
            for f in file_names:
                self.files_listbox.insert(END, f)
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't open ZIP: {e}")

    # When preview image selected, display it
    def preview_selected(self, event=None):
        filename = self.preview_combo.get()
        if filename and filename != "None":
            path = os.path.join("data/zips/previews", filename)
        else:
            path = DEFAULT_IMAGE
        self.display_image(path)

    # Display image on canvas
    def display_image(self, path):
        if not path or not os.path.exists(path):
            path = DEFAULT_IMAGE
        try:
            img = Image.open(path)
            img.thumbnail((200, 200))
            self.current_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(103, 103, image=self.current_image)
        except Exception as e:
            self.canvas.delete("all")
            messagebox.showerror("Error", f"Could not load image:\n{e}")

    def get_files_from_zip(self):
        selected_zip = self.zip_combo.get()
        if not selected_zip:
            messagebox.showwarning("No ZIP Selected", "Please select a ZIP file first.")
            return

        zip_path = os.path.join("data/zips", selected_zip)
        if not os.path.exists(zip_path):
            messagebox.showerror("ZIP Not Found", f"The ZIP file does not exist:\n{zip_path}")
            return

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_names = zip_ref.namelist()

            self.files_listbox.delete(0, END)  # Clear list
            for f in file_names:
                self.files_listbox.insert(END, f)

            self.mark_dirty()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read ZIP file:\n{e}")

    # Browse and copy ZIP file to project folder
    def browse_zip(self):
        path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if path:
            self._manual_zip_path = path
            self.zip_combo.set(os.path.basename(path))
            self.zip_manually_selected = True

            try:
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    file_names = zip_ref.namelist()
                self.files_listbox.delete(0, END)
                for f in file_names:
                    self.files_listbox.insert(END, f)
            except Exception as e:
                messagebox.showerror("Error", f"Couldn't open ZIP: {e}")

            self.mark_dirty()

    # Browse and display preview image
    def browse_preview(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg")])
        if path:
            self._manual_preview_path = path
            self.preview_combo.set(os.path.basename(path))
            self.preview_manually_selected = True
            self.display_image(path)
            self.mark_dirty()

    # Add a new entry
    def add_entry(self):
        self.loading_entry = True  # Make sure this is set!
        self.data.append({
            "title": "New Entry",
            "zip_path": "",
            "preview": "",
            "files": [],
            "chunk_id": "",
            "replaces": "",
            "description": ""
        })
        new_index = len(self.data) - 1
        self.current_index = new_index

        self.entry_listbox.insert(END, "New Entry")
        self.entry_listbox.selection_clear(0, END)
        self.entry_listbox.selection_set(new_index)
        self.entry_listbox.activate(new_index)
        self.entry_listbox.event_generate("<<ListboxSelect>>")

        # Delay finishing load to allow selection event to complete
        self.master.after(50, self._post_add_entry)

    def _post_add_entry(self):
        self.loading_entry = False
        self.mark_dirty()  # Moved here — after loading_entry is reset

    # Delete currently selected entry (with optional file deletion)
    def delete_entry(self):
        idx = self.get_selected_index()
        if idx is not None:
            entry = self.data[idx]
            msg = "Delete the selected entry?"
            zip_path = entry.get("zip_path", "")
            preview_path = entry.get("preview", "")
            files_to_delete = []

            if zip_path and os.path.exists(zip_path):
                files_to_delete.append(zip_path)
            if preview_path and os.path.exists(preview_path):
                files_to_delete.append(preview_path)

            if messagebox.askyesno("Confirm Delete", msg):
                if files_to_delete:
                    if messagebox.askyesno("Delete Files", "Delete associated files from disk?"):
                        for file_path in files_to_delete:
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                messagebox.showerror("Error", f"Failed to delete {file_path}:\n{e}")

                # Refresh preview dropdown if image was deleted
                self.populate_preview_images()

                # Remove from data and UI
                del self.data[idx]
                self.entry_listbox.delete(idx)
                self.clear_details()

                # Refresh other UI components
                self.populate_zip_files()
                self.save_all()

                self.is_dirty = False
                self.save_button.config(text="Saved")
                self.save_button.config(state="disabled")

                # Select next appropriate entry
                new_idx = idx - 1 if idx > 0 else (0 if self.data else None)
                if new_idx is not None and self.data:
                    self.loading_entry = True
                    self.entry_listbox.selection_set(new_idx)
                    self.entry_listbox.activate(new_idx)
                    self.on_entry_select(None)
                    self.loading_entry = False
                else:
                    self.current_index = None
                    self.entry_listbox.selection_clear(0, END)
                    self.clear_details()

                # Extra refresh (optional but safe redundancy)
                self.populate_preview_images()
                self.populate_zip_files()

    def move_entry_up(self):
        idx = self.get_selected_index()
        if idx is None or idx == 0:
            return  # Can't move up the first item

        # Swap data
        self.data[idx - 1], self.data[idx] = self.data[idx], self.data[idx - 1]

        # Update listbox
        title = self.entry_listbox.get(idx)
        self.entry_listbox.delete(idx)
        self.entry_listbox.insert(idx - 1, title)

        # Update selection
        new_idx = idx - 1
        self.entry_listbox.selection_clear(0, END)
        self.entry_listbox.selection_set(new_idx)
        self.entry_listbox.activate(new_idx)

        # Load entry without triggering loading_entry lock
        self.loading_entry = False
        self.display_entry_details(new_idx)

        # Mark dirty and refresh move buttons
        self.mark_dirty()
        self.update_move_buttons()

    def move_entry_down(self):
        idx = self.get_selected_index()
        if idx is None or idx >= len(self.data) - 1:
            return  # Can't move down the last item

        # Swap data
        self.data[idx + 1], self.data[idx] = self.data[idx], self.data[idx + 1]

        # Update listbox
        title = self.entry_listbox.get(idx)
        self.entry_listbox.delete(idx)
        self.entry_listbox.insert(idx + 1, title)

        # Update selection
        new_idx = idx + 1
        self.entry_listbox.selection_clear(0, END)
        self.entry_listbox.selection_set(new_idx)
        self.entry_listbox.activate(new_idx)

        # Load entry without triggering loading_entry lock
        self.loading_entry = False
        self.display_entry_details(new_idx)

        # Mark dirty and refresh move buttons
        self.mark_dirty()
        self.update_move_buttons()

    def update_move_buttons(self):
        idx = self.get_selected_index()
        total = len(self.data)
        if total == 0 or idx is None:
            self.move_up_button.config(state="disabled")
            self.move_down_button.config(state="disabled")
        else:
            self.move_up_button.config(state="normal" if idx > 0 else "disabled")
            self.move_down_button.config(state="normal" if idx < total - 1 else "disabled")

    def display_entry_details(self, idx):
        """
        Helper to display entry details without setting loading_entry flag.
        Used internally after reorder.
        """
        if idx is None or idx >= len(self.data):
            return

        entry = self.data[idx]
        self.current_index = idx

        self.title_var.set(entry.get("title", ""))
        self.chunk_id_var.set(entry.get("chunk_id", ""))
        self.replaces_var.set(entry.get("replaces", ""))
        self.description_entry.delete("1.0", END)
        self.description_entry.insert("1.0", entry.get("description", ""))

        zip_path = entry.get("zip_path", "")
        preview = entry.get("preview", "")

        if zip_path.startswith("data/zips/"):
            filename = os.path.basename(zip_path)
            self.zip_combo.set(filename)
            self.zip_selected(None)
        else:
            self.zip_combo.set("")
            self._manual_zip_path = zip_path

        if preview.startswith("data/zips/previews/"):
            filename = os.path.basename(preview)
            self.preview_combo.set(filename)
            self.display_image(os.path.join("data/zips/previews", filename))
        elif not preview or preview == "None":
            self.preview_combo.set("None")
            self.display_image(DEFAULT_IMAGE)
        else:
            self.preview_combo.set("None")
            self.display_image(preview)

        self.files_listbox.delete(0, END)
        for f in entry.get("files", []):
            self.files_listbox.insert(END, f)


    # Handle listbox selection change
    def on_entry_select(self, event):
        self.loading_entry = True
        try:
            idx = self.get_selected_index()
            if idx is None:
                self.clear_details()
                return

            self.current_index = idx
            entry = self.data[idx]

            self.title_var.set(entry.get("title", ""))
            zip_path = entry.get("zip_path", "")
            preview = entry.get("preview", "")
            self._manual_zip_path = None
            self._manual_preview_path = None
            self.chunk_id_var.set(entry.get("chunk_id", ""))
            self.replaces_var.set(entry.get("replaces", ""))
            self.description_entry.delete("1.0", END)
            self.description_entry.insert("1.0", entry.get("description", ""))

            if zip_path.startswith("data/zips/"):
                filename = os.path.basename(zip_path)
                self.zip_combo.set(filename)
                self.zip_selected(None)
            else:
                self.zip_combo.set("")
                self._manual_zip_path = zip_path

            if preview.startswith("data/zips/previews/"):
                filename = os.path.basename(preview)
                self.preview_combo.set(filename)
                self.display_image(os.path.join("data/zips/previews", filename))
            elif not preview or preview == "None":
                self.preview_combo.set("None")
                self.display_image(DEFAULT_IMAGE)
            else:
                self.preview_combo.set("None")
                self.display_image(preview)

            self.files_listbox.delete(0, END)
            for f in entry.get("files", []):
                self.files_listbox.insert(END, f)

            if not self.is_dirty:
                self.save_button.config(text="Saved")
                self.save_button.config(state="disabled")
        finally:
            # Enable or disable move buttons based on position
            if self.move_up_button and self.move_down_button:
                total = len(self.data)
                if total == 0 or idx is None:
                    self.move_up_button.config(state="disabled")
                    self.move_down_button.config(state="disabled")
                else:
                    self.move_up_button.config(state="normal" if idx > 0 else "disabled")
                    self.move_down_button.config(state="normal" if idx < total - 1 else "disabled")

    # Get selected entry index
    def get_selected_index(self):
        selection = self.entry_listbox.curselection()
        return selection[0] if selection else None

    # Reset all input fields
    def clear_details(self):
        self.title_var.set("")
        self.zip_combo.set("")
        self.preview_combo.set("None")
        self.files_listbox.delete(0, END)
        self.chunk_id_var.set("")
        self.replaces_var.set("")
        self.description_entry.delete("1.0", END)
        self.canvas.delete("all")
        self.display_image(DEFAULT_IMAGE)

    # Show a dialog to add a file name
    def add_file(self):
        def on_ok():
            name = file_entry.get().strip()
            if name:
                self.files_listbox.insert(END, name)
                self.mark_dirty()
            top.destroy()

        top = Toplevel(self.master)
        top.title("Add File")
        Label(top, text="File name:").pack()
        file_entry = Entry(top, width=40)
        file_entry.pack(padx=10, pady=5)
        file_entry.focus()
        Button(top, text="OK", command=on_ok).pack(pady=5)
        top.transient(self.master)
        top.grab_set()
        
        # Center the window on screen
        def center_window():
            top.update_idletasks()
            width = top.winfo_width()
            height = top.winfo_height()
            screen_width = top.winfo_screenwidth()
            screen_height = top.winfo_screenheight()
            x = (screen_width // 2) - (width // 2)
            y = (screen_height // 2) - (height // 2)
            top.geometry(f"{width}x{height}+{x}+{y}")

        top.after(0, center_window)  # Schedule after first draw

        self.master.wait_window(top)

    # Define the handler
    def on_file_select(self, event=None):
        sel = self.files_listbox.curselection()
        if sel:
            self.deleteFileButton.config(state="normal")
        elif not sel:
            self.deleteFileButton.config(state="disabled")

    # Delete selected file from the list
    def delete_file(self):
        sel = self.files_listbox.curselection()
        if sel:
            self.files_listbox.delete(sel[0])
            self.mark_dirty()
            self.on_file_select()  # Update button state after deletion

    # Save current state to JSON file
    def save_all(self):
        idx = self.get_selected_index()
        if idx is not None and idx < len(self.data):
            entry = self.data[idx]
            entry["title"] = self.title_var.get()
            entry["files"] = list(self.files_listbox.get(0, END))
            entry["chunk_id"] = self.chunk_id_var.get()
            entry["replaces"] = self.replaces_var.get()
            entry["description"] = self.description_entry.get("1.0", END).strip()

            # Determine ZIP path
            zip_path = ""
            if self.zip_combo.get():
                zip_path = os.path.join("data/zips", self.zip_combo.get())

                if self.zip_manually_selected and hasattr(self, "_manual_zip_path"):
                    os.makedirs("data/zips", exist_ok=True)
                    shutil.copy(self._manual_zip_path, zip_path)
                    self.zip_manually_selected = False  # Reset flag
                    self.populate_zip_files()

            entry["zip_path"] = zip_path.replace("\\", "/")

            # Determine preview path
            preview_path = ""
            if self.preview_combo.get() and self.preview_combo.get() != "None":
                preview_path = os.path.join("data/zips/previews", self.preview_combo.get())

                if self.preview_manually_selected and hasattr(self, "_manual_preview_path"):
                    os.makedirs("data/zips/previews", exist_ok=True)
                    shutil.copy(self._manual_preview_path, preview_path)
                    self.preview_manually_selected = False  # Reset flag
                    self.populate_preview_images()

            entry["zip_path"] = zip_path.replace("\\", "/")
            entry["preview"] = preview_path.replace("\\", "/")

            # Update title in listbox
            self.entry_listbox.delete(idx)
            self.entry_listbox.insert(idx, entry["title"])
            self.entry_listbox.selection_set(idx)

            self.is_dirty = False
            self.save_button.config(text="Saved")
            self.save_button.config(state="disabled")

        # Always write current data to JSON
        try:
            os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
            mod_name = self.mod_name_var.get().strip() or "UnnamedMod"
            mod_structure = {
                "mod_name": mod_name,
                "entries": self.data
            }

            with open(JSON_FILE, "w") as f:
                json.dump(mod_structure, f, indent=2)

            # messagebox.showinfo("Saved", "Data saved to mod_options.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON:\n{e}")

    # Load entries from JSON file on startup
    def load_json(self):
        if not os.path.exists(JSON_FILE):
            self.data = []
            self.mod_name_var.set("UnnamedMod")
            return

        try:
            with open(JSON_FILE, "r") as f:
                json_data = json.load(f)

            if isinstance(json_data, dict) and "mod_name" in json_data and "entries" in json_data:
                self.mod_name_var.set(json_data["mod_name"])
                self.data = json_data["entries"]
            else:
                self.mod_name_var.set("UnnamedMod")
                self.data = []

            self.entry_listbox.delete(0, END)
            for entry in self.data:
                self.entry_listbox.insert(END, entry.get("title", "Untitled"))
            if self.data:
                self.entry_listbox.selection_set(0)
                self.on_entry_select(None)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load mod_options.json:\n{e}")

        self.is_dirty = False
        self.save_button.config(text="Saved")
        self.save_button.config(state="disabled")

    def create_mod_zip(self):
        # Get mod name and sanitize it
        raw_mod_name = self.mod_name_var.get().strip() or "UnnamedMod"
        mod_name = raw_mod_name.replace(" ", "_")
        zip_filename = f"{mod_name}.zip"

        zip_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")],
            title="Save Mod ZIP As",
            initialfile=zip_filename
        )

        if not zip_path:
            return  # User cancelled

        try:
            # Folder name inside the zip and temp working folder
            temp_dir = os.path.join(tempfile.gettempdir(), mod_name)

            # Clean temp dir if it already exists
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)

            # Copy the data folder (excluding certain assets)
            src_data = "data"
            dst_data = os.path.join(temp_dir, "data")
            def ignore_builder_folder(dir, files):
                if os.path.normpath(dir).endswith(os.path.normpath("data/assets")):
                    return ["options_builder"]
                return []

            shutil.copytree(src_data, dst_data, ignore=ignore_builder_folder)

            # Copy the EXE
            exe_path = "Mod_Option_Selector.exe"
            if os.path.exists(exe_path):
                shutil.copy(exe_path, temp_dir)
            else:
                messagebox.showwarning("Missing File", f"{exe_path} not found. Only 'data/' will be packaged.")

            # Create the zip
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for foldername, subfolders, filenames in os.walk(temp_dir):
                    for filename in filenames:
                        file_path = os.path.join(foldername, filename)
                        arcname = os.path.join(mod_name, os.path.relpath(file_path, temp_dir))
                        zipf.write(file_path, arcname)

            # Clean up
            shutil.rmtree(temp_dir, ignore_errors=True)

            self.show_zip_success_popup(zip_path)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to create zip:\n{e}")

    def show_zip_success_popup(self, zip_path):
        popup = tk.Toplevel(self.root)
        popup.title("Success")
        popup.resizable(False, False)

        label = tk.Label(popup, text=f"Mod packaged successfully:\n{zip_path}", wraplength=300)
        label.pack(padx=10, pady=(10, 5))

        # Button container
        button_frame = tk.Frame(popup)
        button_frame.pack(pady=(0, 10))

        def open_in_explorer():
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", os.path.normpath(zip_path)])
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", zip_path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(zip_path)])
            popup.destroy()  # Close popup after opening location

        open_button = tk.Button(button_frame, text="Open Location", command=open_in_explorer)
        open_button.pack(side="left", padx=5)

        ok_button = tk.Button(button_frame, text="OK", command=popup.destroy)
        ok_button.pack(side="left", padx=5)

        # Center the popup on screen
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        popup.geometry(f"+{x}+{y}")

class ToolTip:
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
            x = event.x_root + 30
            y = event.y_root - 30  # appear above cursor
            self.tip_window.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# Launch the app if run directly
if __name__ == "__main__":
    root = Tk()
    root.iconbitmap("data/assets/options_builder/mod_option_builder_icon.ico")  # Set main app window icon
    root.geometry("900x400")
    root.minsize(1050, 600)  # Set minimum window size
    app = JsonBuilderApp(root)

    # Center the window on screen
    def center_window():
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

    root.after(0, center_window)  # Schedule after first draw

    root.mainloop()

# After app exits, unlock and remove the lock file to allow future runs
try:
    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    lock_file.close()
    os.remove(lock_file_path)
except Exception:
    # Silently ignore any errors during cleanup
    pass