"""
Bezel Launcher - Ultimate Edition for Arcade Cabinets & Retro Gaming
Requirements: pip install pillow psutil
"""
import os
import sys
import json
import time
import ctypes
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

try:
    import psutil
except ImportError:
    psutil = None

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
LIBRARY_FILE = os.path.join(BASE_DIR, "games.json")

KEY_COLOR = (1, 1, 1)
KEY_HEX = "#010101"
STARTUP_GRACE = 8
END_GRACE = 3

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
VK_CONTROL, VK_MENU, VK_B = 0x11, 0x12, 0x42


class BezelLauncher:
    def __init__(self, root):
        self.root = root
        root.title("Bezel Launcher Ultimate")
        root.geometry("780x520")

        self.games = []
        self.process = None
        self.helper_process = None
        self.overlay = None
        self.hwnd = None
        self.game_dir = ""
        self.proc_name = ""
        self.last_alive = 0

        self.v_name = tk.StringVar()
        self.v_exe = tk.StringVar()
        self.v_png = tk.StringVar()
        self.v_proc = tk.StringVar()
        self.v_helper = tk.StringVar()

        self.build_ui()
        self.load_library()
        self.refresh_list()

        if psutil is None:
            messagebox.showwarning(
                "Missing psutil",
                "Please install psutil for reliable process tracking:\n\npip install psutil")

    def build_ui(self):
        left = ttk.Frame(self.root, padding=10)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Game Library", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(left, columns=("name",), show="", height=14, selectmode="browse")
        self.tree.column("name", width=250)
        self.tree.pack(fill="both", expand=True, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.launch_selected())

        tk.Button(left, text="🚀 LAUNCH WITH BEZEL", bg="#2e7d32", fg="white",
                  font=("Segoe UI", 10, "bold"), height=2,
                  command=self.launch_selected).pack(fill="x", pady=(0, 5))

        tk.Button(left, text="📦 Create Standalone .py for this Game", bg="#1565c0", fg="white",
                  font=("Segoe UI", 9), command=self.create_standalone_script).pack(fill="x")

        right = ttk.Frame(self.root, padding=10)
        right.pack(side="right", fill="y")

        def row(label, var, browse=None):
            ttk.Label(right, text=label).pack(anchor="w", pady=(6, 0))
            f = ttk.Frame(right)
            f.pack(fill="x")
            ttk.Entry(f, textvariable=var, width=38).pack(side="left")
            if browse:
                ttk.Button(f, text="...", width=3, command=browse).pack(side="left", padx=3)

        row("Game Title", self.v_name)
        row("Executable (.exe)", self.v_exe, self.browse_exe)
        row("Bezel Overlay (.png)", self.v_png, self.browse_png)
        row("Process to Monitor (Optional)", self.v_proc)
        row("Helper App (e.g. x360ce / XOutput)", self.v_helper, self.browse_helper)

        btns = ttk.Frame(right)
        btns.pack(fill="x", pady=15)
        ttk.Button(btns, text="Save / Add", command=self.save_game).pack(side="left")
        ttk.Button(btns, text="New", command=self.clear_form).pack(side="left", padx=5)
        ttk.Button(btns, text="Remove", command=self.remove_game).pack(side="left")

        ttk.Label(right, foreground="gray",
                  text="Emergency Exit: Ctrl+Alt+B or F4").pack(anchor="w", side="bottom")

    def browse_exe(self):
        f = filedialog.askopenfilename(filetypes=[("Executables", "*.exe *.bat *.cmd")])
        if f:
            self.v_exe.set(f)
            if not self.v_name.get():
                self.v_name.set(os.path.splitext(os.path.basename(f))[0])

    def browse_png(self):
        f = filedialog.askopenfilename(filetypes=[("PNG Bezel", "*.png")])
        if f:
            self.v_png.set(f)

    def browse_helper(self):
        f = filedialog.askopenfilename(filetypes=[("Executables", "*.exe *.bat *.cmd")])
        if f:
            self.v_helper.set(f)

    def load_library(self):
        try:
            with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                self.games = json.load(f)
        except Exception:
            self.games = []

    def save_library(self):
        try:
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.games, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save library:\n{e}")

    def refresh_list(self, select=None):
        self.tree.delete(*self.tree.get_children())
        for i, g in enumerate(self.games):
            self.tree.insert("", "end", iid=str(i), values=(g["name"],))
        if select is not None and str(select) in self.tree.get_children():
            self.tree.selection_set(str(select))

    def selected_index(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def on_select(self, _=None):
        i = self.selected_index()
        if i is None:
            return
        g = self.games[i]
        self.v_name.set(g["name"])
        self.v_exe.set(g["exe"])
        self.v_png.set(g["png"])
        self.v_proc.set(g.get("proc", ""))
        self.v_helper.set(g.get("helper", ""))

    def clear_form(self):
        self.tree.selection_remove(self.tree.selection())
        for v in (self.v_name, self.v_exe, self.v_png, self.v_proc, self.v_helper):
            v.set("")

    def save_game(self):
        name, exe, png = self.v_name.get().strip(), self.v_exe.get().strip(), self.v_png.get().strip()
        if not name or not os.path.exists(exe) or not os.path.exists(png):
            messagebox.showerror("Error", "Please provide a valid name, executable path, and PNG bezel path.")
            return
        
        entry = {
            "name": name, 
            "exe": exe, 
            "png": png, 
            "proc": self.v_proc.get().strip(),
            "helper": self.v_helper.get().strip()
        }
        i = self.selected_index()
        if i is None:
            self.games.append(entry)
            i = len(self.games) - 1
        else:
            self.games[i] = entry
        self.save_library()
        self.refresh_list(select=i)

    def remove_game(self):
        i = self.selected_index()
        if i is None:
            return
        if messagebox.askyesno("Remove", f"Remove '{self.games[i]['name']}' from library?"):
            del self.games[i]
            self.save_library()
            self.clear_form()
            self.refresh_list()

    def create_standalone_script(self):
        i = self.selected_index()
        if i is None:
            messagebox.showinfo("Notice", "Please select a game from the list first.")
            return
        g = self.games[i]
        safe_name = "".join(c for c in g["name"] if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        script_path = os.path.join(desktop, f"Launch_{safe_name}.py")

        code_template = f'''import os, sys, time, ctypes, subprocess, tkinter as tk
from PIL import Image, ImageTk
try: import psutil
except: psutil = None

EXE_PATH = r"{g['exe']}"
PNG_PATH = r"{g['png']}"
PROC_NAME = "{g.get('proc', '')}".lower()
HELPER_PATH = r"{g.get('helper', '')}"

root = tk.Tk()
root.withdraw()
sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()

helper_process = None
if HELPER_PATH and os.path.exists(HELPER_PATH):
    try:
        h_dir = os.path.dirname(os.path.abspath(HELPER_PATH))
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 7
        helper_process = subprocess.Popen([HELPER_PATH], cwd=h_dir, startupinfo=si)
    except Exception as e:
        print("Helper error:", e)

ov = tk.Toplevel(root)
ov.overrideredirect(True)
ov.geometry(f"{{sw}}x{{sh}}+0+0")
ov.config(bg="#010101")
ov.wm_attributes("-transparentcolor", "#010101")
ov.wm_attributes("-topmost", True)

img = Image.open(PNG_PATH).convert("RGBA").resize((sw, sh), Image.Resampling.LANCZOS)
bg = Image.new("RGBA", (sw, sh), (1, 1, 1, 255))
bg.alpha_composite(img)
tk_img = ImageTk.PhotoImage(bg.convert("RGB"))
tk.Label(ov, image=tk_img, bg="#010101", bd=0).pack(fill="both", expand=True)
ov.update()

user32 = ctypes.windll.user32
hwnd = user32.GetParent(ov.winfo_id()) or ov.winfo_id()
style = user32.GetWindowLongW(hwnd, -20)
user32.SetWindowLongW(hwnd, -20, style | 0x00080000 | 0x00000020 | 0x08000000 | 0x00000080)
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0|2|16|64)

game_dir = os.path.dirname(os.path.abspath(EXE_PATH))
process = subprocess.Popen([EXE_PATH], cwd=game_dir)

def make_borderless_and_center():
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    def enum_windows_callback(hwnd_w, extra):
        if user32.IsWindowVisible(hwnd_w):
            length = user32.GetWindowTextLengthW(hwnd_w)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd_w, buff, length + 1)
            if length > 0 and "Bezel" not in buff.value:
                st = user32.GetWindowLongW(hwnd_w, -16)
                user32.SetWindowLongW(hwnd_w, -16, st & ~0x00C00000 & ~0x00040000)
                rect = RECT()
                user32.GetWindowRect(hwnd_w, ctypes.byref(rect))
                cur_w, cur_h = rect.right - rect.left, rect.bottom - rect.top
                x, y = (sw - cur_w) // 2, (sh - cur_h) // 2
                user32.SetWindowPos(hwnd_w, 0, x, y, 0, 0, 1|32|64)
                return False
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(enum_windows_callback), 0)

root.after(1200, make_borderless_and_center)

def check_alive():
    if (process and process.poll() is None) or (psutil and any(p.info['exe'] and p.info['exe'].lower().startswith(game_dir.lower()) for p in psutil.process_iter(['exe']))):
        root.after(1000, check_alive)
    else:
        if helper_process and helper_process.poll() is None:
            try: helper_process.terminate()
            except: pass
        ov.destroy()
        root.destroy()

root.after(1000, check_alive)
root.mainloop()
'''
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code_template)
            messagebox.showinfo("Success", f"Standalone script successfully created on Desktop:\n{os.path.basename(script_path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def launch_selected(self):
        i = self.selected_index()
        if i is None:
            messagebox.showinfo("Bezel Launcher", "Please select a game from the list.")
            return
        g = self.games[i]
        if not os.path.exists(g["exe"]) or not os.path.exists(g["png"]):
            messagebox.showerror("Error", "Game executable or bezel PNG path is no longer valid.")
            return

        self.game_dir = os.path.dirname(os.path.abspath(g["exe"]))
        self.proc_name = g.get("proc", "").lower()
        helper_path = g.get("helper", "").strip()

        self.root.withdraw()

        self.helper_process = None
        if helper_path and os.path.exists(helper_path):
            try:
                h_dir = os.path.dirname(os.path.abspath(helper_path))
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 7
                self.helper_process = subprocess.Popen([helper_path], cwd=h_dir, startupinfo=si)
            except Exception as e:
                print("Could not start helper app:", e)

        self.create_overlay(g["png"])

        try:
            self.process = subprocess.Popen([g["exe"]], cwd=self.game_dir)
        except Exception as e:
            self.close_overlay()
            messagebox.showerror("Launch Error", str(e))
            return

        self.root.after(1200, self.make_borderless_and_center)
        self.last_alive = time.time() + STARTUP_GRACE
        self.root.after(1000, self.monitor)
        self.root.after(500, self.keep_on_top)

    def make_borderless_and_center(self):
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        def enum_windows_callback(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                
                if length > 0 and "Bezel" not in buff.value:
                    GWL_STYLE = -16
                    WS_CAPTION = 0x00C00000
                    WS_THICKFRAME = 0x00040000
                    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    style &= ~WS_CAPTION
                    style &= ~WS_THICKFRAME
                    user32.SetWindowLongW(hwnd, GWL_STYLE, style)

                    rect = RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    cur_w = rect.right - rect.left
                    cur_h = rect.bottom - rect.top

                    x = (sw - cur_w) // 2
                    y = (sh - cur_h) // 2

                    SWP_FRAMECHANGED = 0x0020
                    SWP_SHOWWINDOW = 0x0040
                    user32.SetWindowPos(hwnd, 0, x, y, 0, 0, SWP_NOSIZE | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                    return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)

    def create_overlay(self, png_path):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()

        ov = tk.Toplevel(self.root)
        ov.overrideredirect(True)
        ov.geometry(f"{sw}x{sh}+0+0")
        ov.config(bg=KEY_HEX)
        ov.wm_attributes("-transparentcolor", KEY_HEX)
        ov.wm_attributes("-topmost", True)

        img = Image.open(png_path).convert("RGBA").resize((sw, sh), Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", (sw, sh), KEY_COLOR + (255,))
        bg.alpha_composite(img)
        self.tk_img = ImageTk.PhotoImage(bg.convert("RGB"))

        lbl = tk.Label(ov, image=self.tk_img, bg=KEY_HEX, bd=0)
        lbl.pack(fill="both", expand=True)
        ov.update()

        user32 = ctypes.windll.user32
        hwnd = user32.GetParent(ov.winfo_id()) or ov.winfo_id()
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

        self.overlay, self.hwnd = ov, hwnd
        self.force_top()

    def force_top(self):
        ctypes.windll.user32.SetWindowPos(
            self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

    def keep_on_top(self):
        if self.overlay:
            self.force_top()
            self.root.after(500, self.keep_on_top)

    def close_overlay(self):
        if self.helper_process and self.helper_process.poll() is None:
            try:
                self.helper_process.terminate()
            except:
                pass
        self.helper_process = None

        if self.overlay:
            self.overlay.destroy()
        self.overlay = self.hwnd = None
        self.process = None
        self.root.deiconify()

    def hotkey_pressed(self):
        gs = ctypes.windll.user32.GetAsyncKeyState
        return all(gs(k) & 0x8000 for k in (VK_CONTROL, VK_MENU, VK_B)) or (gs(0x73) & 0x8000)

    def game_alive(self):
        if self.process and self.process.poll() is None:
            return True
        if psutil is None:
            return False
        me = os.getpid()
        gdir = self.game_dir.lower()
        for p in psutil.process_iter(["pid", "name", "exe"]):
            try:
                if p.info["pid"] == me:
                    continue
                if self.proc_name and (p.info["name"] or "").lower() == self.proc_name:
                    return True
                exe = (p.info["exe"] or "").lower()
                if not self.proc_name and exe and exe.startswith(gdir):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def monitor(self):
        if not self.overlay:
            return
        if self.hotkey_pressed():
            if self.process and self.process.poll() is None:
                try: self.process.terminate()
                except: pass
            self.close_overlay()
            return
        if self.game_alive():
            self.last_alive = max(self.last_alive, time.time())
        elif time.time() - self.last_alive > END_GRACE:
            self.close_overlay()
            return
        self.root.after(1000, self.monitor)


if __name__ == "__main__":
    root = tk.Tk()
    BezelLauncher(root)
    root.mainloop()