#!/usr/bin/env python3
"""
Simple Tkinter Contacts App
- Collects Name, Address, and Phone
- Appends entries to a CSV file (default: contacts.csv next to this script)
- Remembers whatever you were typing (unsaved form values) between runs via state.json
- Lets you pick the CSV location if you want
"""

import csv
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime

APP_TITLE = "Simple Contacts App"
STATE_FILENAME = "state.json"
DEFAULT_CSV = "contacts.csv"


def script_dir() -> str:
    # Try to place files next to the script. Fallback to current working directory if __file__ is missing.
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def sanitize_phone(raw: str) -> str:
    digits = [c for c in raw if c.isdigit()]
    if not digits:
        return ""
    # Basic US-formatting when 10 digits; otherwise return digits joined
    if len(digits) == 10:
        return f"({''.join(digits[0:3])}) {''.join(digits[3:6])}-{''.join(digits[6:10])}"
    return ''.join(digits)


class ContactsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("520x420")
        self.minsize(520, 420)

        # Resolve paths
        self._base_dir = script_dir()
        self._state_path = os.path.join(self._base_dir, STATE_FILENAME)

        # Load state before building UI so defaults are ready
        self.state = self._load_state()

        # CSV path
        self.csv_path_var = tk.StringVar(value=self.state.get("csv_path") or os.path.join(self._base_dir, DEFAULT_CSV))

        # Form variables
        self.name_var = tk.StringVar(value=self.state.get("form", {}).get("name", ""))
        self.phone_var = tk.StringVar(value=self.state.get("form", {}).get("phone", ""))

        self._build_ui()

        # Restore address (multiline) after widgets exist
        self.addr_text.insert("1.0", self.state.get("form", {}).get("address", ""))

        # Wire close handler to persist state
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    # ---------- UI ----------
    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        # CSV location row
        csv_row = ttk.Frame(outer)
        csv_row.pack(fill="x", pady=(0, 8))
        ttk.Label(csv_row, text="CSV File:").pack(side="left")
        csv_entry = ttk.Entry(csv_row, textvariable=self.csv_path_var)
        csv_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Button(csv_row, text="Browse…", command=self.choose_csv).pack(side="left")

        form = ttk.LabelFrame(outer, text="Contact Details", padding=12)
        form.pack(fill="both", expand=True)

        # Name
        name_row = ttk.Frame(form)
        name_row.pack(fill="x", pady=6)
        ttk.Label(name_row, text="Name:", width=12).pack(side="left")
        name_entry = ttk.Entry(name_row, textvariable=self.name_var)
        name_entry.pack(side="left", fill="x", expand=True)
        name_entry.focus_set()

        # Address (multiline)
        addr_row = ttk.Frame(form)
        addr_row.pack(fill="both", expand=True, pady=6)
        ttk.Label(addr_row, text="Address:", width=12).pack(side="left", anchor="n", pady=(4,0))
        self.addr_text = tk.Text(addr_row, height=5, wrap="word")
        self.addr_text.pack(side="left", fill="both", expand=True)

        # Phone
        phone_row = ttk.Frame(form)
        phone_row.pack(fill="x", pady=6)
        ttk.Label(phone_row, text="Phone:", width=12).pack(side="left")
        phone_entry = ttk.Entry(phone_row, textvariable=self.phone_var)
        phone_entry.pack(side="left", fill="x", expand=True)

        # Buttons
        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(8,0))
        ttk.Button(btns, text="Save Entry", command=self.save_entry).pack(side="left")
        ttk.Button(btns, text="Clear Form", command=self.clear_form).pack(side="left", padx=8)
        ttk.Button(btns, text="Open CSV", command=self.open_csv_folder).pack(side="left")
        ttk.Button(btns, text="Exit", command=self.on_exit).pack(side="right")

        # Hint / status
        note = ttk.Label(
            outer,
            foreground="#555555",
            text="Tip: The app remembers what you were typing if you close it before saving. "
                 "Saved entries are appended to the CSV."
        )
        note.pack(fill="x", pady=(10,0))

    # ---------- Actions ----------
    def choose_csv(self):
        path = filedialog.asksaveasfilename(
            title="Choose or create a CSV file",
            initialdir=os.path.dirname(self.csv_path_var.get()),
            initialfile=os.path.basename(self.csv_path_var.get()),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if path:
            self.csv_path_var.set(path)
            self._save_state()  # persist choice immediately

    def open_csv_folder(self):
        path = self.csv_path_var.get()
        if not path:
            messagebox.showinfo(APP_TITLE, "Choose a CSV file first.")
            return
        folder = os.path.dirname(path)
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Could not open folder:\n{e}")

    def clear_form(self):
        self.name_var.set("")
        self.addr_text.delete("1.0", "end")
        self.phone_var.set("")
        self._save_state()  # keep state consistent

    def save_entry(self):
        name = self.name_var.get().strip()
        address = self.addr_text.get("1.0", "end").strip()
        phone = sanitize_phone(self.phone_var.get().strip())

        if not name:
            messagebox.showwarning(APP_TITLE, "Please enter a name.")
            return
        if not address:
            messagebox.showwarning(APP_TITLE, "Please enter an address.")
            return
        if not phone:
            # allow empty phone? For now, require something.
            if not messagebox.askyesno(APP_TITLE, "Phone is empty or invalid. Save anyway?"):
                return

        path = self.csv_path_var.get().strip()
        if not path:
            messagebox.showwarning(APP_TITLE, "Please choose a CSV file location.")
            return

        # Ensure directory exists
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        is_new_file = not os.path.exists(path) or os.path.getsize(path) == 0

        try:
            with open(path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if is_new_file:
                    writer.writerow(["timestamp", "name", "address", "phone"])
                writer.writerow([datetime.now().isoformat(timespec="seconds"), name, address, phone])
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Could not write to CSV:\n{e}")
            return

        # After saving, also update the remembered form so you can "pick up" later if desired
        self._save_state()
        messagebox.showinfo(APP_TITLE, "Entry saved to CSV.")
        # Optionally clear after save (comment this out if you prefer keeping values)
        self.clear_form()

    def on_exit(self):
        self._save_state()
        self.destroy()

    # ---------- State (persistence of unsaved form + csv path) ----------
    def _load_state(self) -> dict:
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except FileNotFoundError:
            return {}
        except Exception:
            # Corrupt state file—ignore
            return {}

    def _save_state(self):
        data = {
            "csv_path": self.csv_path_var.get().strip(),
            "form": {
                "name": self.name_var.get(),
                "address": self.addr_text.get("1.0", "end").strip(),
                "phone": self.phone_var.get(),
            }
        }
        try:
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            # Don't crash app due to state save failure
            pass


def main():
    app = ContactsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
