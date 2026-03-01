import os
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

CONFIG_FILE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "WorkspaceLauncher", "app_groups.json")
APP_DIR = os.path.dirname(CONFIG_FILE)

START_MENU_DIRS = [
    os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
    os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    os.path.join(os.environ.get("USERPROFILE", ""), r"Desktop"),
    os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), r"Desktop"),
]

SHORTCUT_EXTS = {".lnk", ".url", ".appref-ms"}


def _ensure_app_dir():
    os.makedirs(APP_DIR, exist_ok=True)


def load_groups():
    _ensure_app_dir()
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # Expect {group_name: [{"name": str, "path": str}, ...]}
            return data
        return {}
    except Exception:
        return {}


def save_groups(groups: dict):
    _ensure_app_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2)


def scan_shortcuts():
    """Return list of {'name': display_name, 'path': shortcut_path} from Start Menu + Desktop."""
    found = {}
    for base in START_MENU_DIRS:
        if not base or not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in SHORTCUT_EXTS:
                    full_path = os.path.join(root, file)
                    name = os.path.splitext(file)[0].strip()
                    if name and name not in found:
                        found[name] = full_path
    apps = [{"name": n, "path": p} for n, p in found.items()]
    apps.sort(key=lambda x: x["name"].lower())
    return apps


def launch_path(path: str):
    # os.startfile works for .lnk, .url, .appref-ms
    os.startfile(path)


def get_startup_folder():
    # per-user startup folder
    return os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")


def set_startup(enable: bool):
    """Enable/disable startup by dropping a .bat file in Startup folder.
    Bat launches this script with pythonw (no console)."""
    startup = get_startup_folder()
    if not startup or not os.path.isdir(startup):
        raise RuntimeError("Startup folder not found")

    bat_path = os.path.join(startup, "WorkspaceLauncher.bat")

    if not enable:
        if os.path.exists(bat_path):
            os.remove(bat_path)
        return

    script_path = os.path.abspath(__file__)

    pyw = "pythonw"
    # If the user ran with a specific python.exe, try to locate pythonw.exe next to it.
    try:
        import sys
        exe = sys.executable
        if exe.lower().endswith("python.exe"):
            candidate = exe[:-len("python.exe")] + "pythonw.exe"
            if os.path.exists(candidate):
                pyw = f'"{candidate}"'
        else:
            pyw = f'"{exe}"'
    except Exception:
        pass

    cmd = f"{pyw} \"{script_path}\""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write(cmd + "\n")


def is_startup_enabled():
    startup = get_startup_folder()
    if not startup:
        return False
    return os.path.exists(os.path.join(startup, "WorkspaceLauncher.bat"))


class ScrollableChecks(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._resize_inner)

        self.vars = {}  # display_name -> BooleanVar

    def _resize_inner(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def set_items(self, items, preselect_names=None):
        preselect_names = set(preselect_names or [])
        for child in self.inner.winfo_children():
            child.destroy()
        self.vars.clear()

        for name in items:
            var = tk.BooleanVar(value=(name in preselect_names))
            cb = ttk.Checkbutton(self.inner, text=name, variable=var)
            cb.pack(anchor="w", pady=2, padx=6)
            self.vars[name] = var

    def get_selected(self):
        return [name for name, var in self.vars.items() if var.get()]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Workspace Launcher")
        self.geometry("900x560")
        self.minsize(880, 540)

        self.groups = load_groups()
        self.apps = scan_shortcuts()
        self.app_map = {a["name"]: a["path"] for a in self.apps}

        self.container = ttk.Frame(self, padding=10)
        self.container.pack(fill="both", expand=True)

        self.home_page = HomePage(self.container, self)
        self.create_page = CreateGroupPage(self.container, self)

        self.home_page.grid(row=0, column=0, sticky="nsew")
        self.create_page.grid(row=0, column=0, sticky="nsew")

        self.show_home()

    def rescan(self):
        self.apps = scan_shortcuts()
        self.app_map = {a["name"]: a["path"] for a in self.apps}

    def add_group(self, name, app_names):
        items = []
        missing = []
        for n in app_names:
            p = self.app_map.get(n)
            if p:
                items.append({"name": n, "path": p})
            else:
                missing.append(n)
        self.groups[name] = items
        save_groups(self.groups)
        if missing:
            messagebox.showwarning("Some apps missing", "These apps were selected but no shortcut path was found:\n\n" + "\n".join(missing[:30]))
        self.show_home()

    def delete_group(self, name):
        if name in self.groups:
            del self.groups[name]
            save_groups(self.groups)

    def launch_group(self, name):
        items = self.groups.get(name, [])
        if not items:
            messagebox.showinfo("Empty group", "This group has no apps.")
            return

        failed = []
        launched = 0
        for item in items:
            p = item.get("path")
            if not p or not os.path.exists(p):
                failed.append(item.get("name", "(unknown)"))
                continue
            try:
                launch_path(p)
                launched += 1
                time.sleep(0.15)
            except Exception:
                failed.append(item.get("name", "(unknown)"))

        msg = f"Launched {launched} app(s)."
        if failed:
            msg += "\n\nFailed:\n- " + "\n- ".join(failed[:20])
        messagebox.showinfo("Launch", msg)

    def show_home(self):
        self.home_page.refresh()
        self.home_page.tkraise()

    def show_create(self, edit_name=None):
        self.create_page.load_apps(edit_name=edit_name)
        self.create_page.tkraise()


class HomePage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        top = ttk.Frame(self)
        top.pack(fill="x")

        ttk.Label(top, text="Home", font=("Segoe UI", 16, "bold")).pack(side="left")

        self.startup_var = tk.BooleanVar(value=False)
        self.startup_chk = ttk.Checkbutton(top, text="Run on startup", variable=self.startup_var, command=self._toggle_startup)
        self.startup_chk.pack(side="right")

        ttk.Button(top, text="Rescan apps", command=self._rescan).pack(side="right", padx=10)

        ttk.Label(self, text="Saved launch groups (double-click to launch):").pack(anchor="w", pady=(12, 4))

        self.group_list = tk.Listbox(self, height=14)
        self.group_list.pack(fill="both", expand=True)
        self.group_list.bind("<Double-Button-1>", self._launch_selected)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=12)

        ttk.Button(btns, text="Create launch group", command=lambda: self.app.show_create()).pack(side="left")
        ttk.Button(btns, text="Edit selected", command=self._edit_selected).pack(side="left", padx=8)
        ttk.Button(btns, text="Delete selected", command=self._delete_selected).pack(side="left")

        self.status = ttk.Label(self, text="", padding=6)
        self.status.pack(fill="x")

    def refresh(self):
        self.group_list.delete(0, tk.END)
        for name in sorted(self.app.groups.keys(), key=lambda x: x.lower()):
            self.group_list.insert(tk.END, name)

        self.startup_var.set(is_startup_enabled())
        self.status.config(text=f"Groups: {len(self.app.groups)} | Apps found: {len(self.app.apps)}")

    def _get_selected_name(self):
        sel = self.group_list.curselection()
        if not sel:
            return None
        return self.group_list.get(sel[0])

    def _launch_selected(self, event=None):
        name = self._get_selected_name()
        if not name:
            return
        self.app.launch_group(name)

    def _delete_selected(self):
        name = self._get_selected_name()
        if not name:
            messagebox.showinfo("Select", "Select a group first.")
            return
        if not messagebox.askyesno("Delete", f"Delete '{name}'?"):
            return
        self.app.delete_group(name)
        self.app.show_home()

    def _edit_selected(self):
        name = self._get_selected_name()
        if not name:
            messagebox.showinfo("Select", "Select a group first.")
            return
        self.app.show_create(edit_name=name)

    def _rescan(self):
        self.app.rescan()
        self.refresh()

    def _toggle_startup(self):
        try:
            set_startup(self.startup_var.get())
        except Exception as e:
            messagebox.showerror("Startup", str(e))
            self.startup_var.set(is_startup_enabled())


class CreateGroupPage(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app
        self.edit_name = None

        top = ttk.Frame(self)
        top.pack(fill="x")

        ttk.Label(top, text="Create launch group", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(top, text="Back", command=self.app.show_home).pack(side="right")

        search_row = ttk.Frame(self)
        search_row.pack(fill="x", pady=(12, 6))

        ttk.Label(search_row, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        ttk.Button(search_row, text="Rescan", command=self._rescan).pack(side="right")

        self.checks = ScrollableChecks(self)
        self.checks.pack(fill="both", expand=True)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=10)

        ttk.Button(bottom, text="Save", command=self._save).pack(side="left")
        ttk.Button(bottom, text="Cancel", command=self.app.show_home).pack(side="left", padx=8)

        self.status = ttk.Label(self, text="", padding=6)
        self.status.pack(fill="x")

    def load_apps(self, edit_name=None):
        self.edit_name = edit_name
        self.app.rescan()
        self.search_var.set("")

        pre = []
        if edit_name and edit_name in self.app.groups:
            pre = [x.get("name") for x in self.app.groups[edit_name] if x.get("name")]

        names = [a["name"] for a in self.app.apps]
        self.checks.set_items(names, preselect_names=pre)

        if edit_name:
            self.status.config(text=f"Editing: {edit_name}")
        else:
            self.status.config(text=f"Select apps and Save")

        self.search_entry.focus_set()

    def _rescan(self):
        self.load_apps(edit_name=self.edit_name)

    def _apply_filter(self):
        q = self.search_var.get().strip().lower()
        names = [a["name"] for a in self.app.apps if (not q or q in a["name"].lower())]

        pre = []
        if self.edit_name and self.edit_name in self.app.groups:
            pre = [x.get("name") for x in self.app.groups[self.edit_name] if x.get("name")]

        # Keep checked state when filtering
        currently_selected = set(self.checks.get_selected())
        preselect = list(set(pre) | currently_selected)

        self.checks.set_items(names, preselect_names=preselect)
        self.status.config(text=f"Showing {len(names)} apps")

    def _save(self):
        selected = self.checks.get_selected()
        if not selected:
            messagebox.showinfo("No apps", "Select at least 1 app.")
            return

        if self.edit_name:
            name = self.edit_name
        else:
            name = simpledialog.askstring("Group name", "Name this launch group:")
            if not name:
                return
            name = name.strip()
            if not name:
                return
            if name in self.app.groups:
                messagebox.showerror("Exists", "That group name already exists.")
                return

        self.app.add_group(name, selected)


if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    App().mainloop()
