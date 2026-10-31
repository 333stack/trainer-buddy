"""Trainer Buddy for Windows: Red (FireRed/LeafGreen look) walks after the mouse pointer, a
Pokémon walks behind him. Same behaviour as the Linux version.

Needs only Python 3 from python.org (tkinter is included). No pip packages.
Or use dist/TrainerBuddy.exe (built by build-exe.sh): no Python needed; double-click it and it
offers to install itself. The exe takes the same options (TrainerBuddy.exe --settings, --quit...).
    pyw trainer_buddy.pyw              run it (no console window)
    pyw trainer_buddy.pyw --settings   pick the Pokémon; the running buddy switches live
    pyw trainer_buddy.pyw --install    copy to %LOCALAPPDATA%\\TrainerBuddy, start with Windows, Start menu entries
    pyw trainer_buddy.pyw --uninstall  remove those again
    py  trainer_buddy.pyw --selftest   logic and sprite checks
    pyw trainer_buddy.pyw --quit       stop the running buddy (or end pythonw.exe in Task Manager)

Sprites in sprites/: red.png is pret/pokefirered red_normal.png plus the run frames 3-11 of
red_surf_run.png (as sPicTable_RedNormal builds it), dust.png is FireRed ground_impact_dust,
the followers' sheets come from rh-hideout/pokeemerald-expansion; all recolored with their game
palettes. Nintendo's art: personal use only.
"""
import math
import os
import shutil
import subprocess
import sys
import tkinter as tk
from collections import deque

FROZEN = getattr(sys, "frozen", False)           # running as the PyInstaller TrainerBuddy.exe
HERE = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
# the exe unpacks its bundled sprites to a temp folder (sys._MEIPASS) on each start
ASSETS = os.path.join(getattr(sys, "_MEIPASS", HERE), "sprites")
EXE_NAME = "TrainerBuddy.exe"
APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
CONFIG = os.path.join(APPDATA, "TrainerBuddy", "follower")
PIDFILE = os.path.join(APPDATA, "TrainerBuddy", "running.pid")
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "TrainerBuddy")
SCALE = 2               # GBA pixels -> screen pixels
SIZE = 16 * SCALE       # Red's tile
SPEED = 4               # px per frame (game walks 1 px per frame at 1x)
RUN_START = 300         # pointer this far from Red: he sprints (double speed) ...
RUN_STOP = 120          # ... until it is this close again
DUST_PUFF = True        # dust puff at Red's feet when he starts sprinting (FireRed ground_impact_dust)
KEEP_OFF = 40           # stop this far from the pointer so the black cursor stays visible
AXIS_STICK = 8          # px the other axis must lead by before Red turns (stops jitter on diagonals)
L_PATH = True           # True: walk diagonals as an L (one straight leg, then turn once).
                        # False: old pathing, zig-zags along diagonals.
FPS = 33
STEP_TICKS = 6          # ticks per animation frame
CONFIG_POLL_MS = 500    # how often the running buddy checks for a new --settings choice
KEY = "#ff00ff"         # colour-key for transparent windows; no sprite uses it (all sprites have hard alpha)

# Sheets are frames side by side; right = mirrored left.
# Each walk cycle is (frame, mirrored) per step, as in the game.
# FireRed player sheet: 16x32 frames: 0 down, 1 up, 2 left, 3-4 down-walk, 5-6 up-walk, 7-8 left-walk,
# 9-11 run down, 12-14 run up, 15-17 run left (each: stride, foot A, stride, foot B like sAnim_RunSouth).
RED = {
    "w": 16, "h": 32, "scale": SCALE,
    "cycles": {
        "down":  [(0, False), (3, False), (0, False), (4, False)],
        "up":    [(1, False), (5, False), (1, False), (6, False)],
        "left":  [(2, False), (7, False), (2, False), (8, False)],
        "right": [(2, True), (7, True), (2, True), (8, True)],
    },
    "run_cycles": {
        "down":  [(9, False), (10, False), (9, False), (11, False)],
        "up":    [(12, False), (13, False), (12, False), (14, False)],
        "left":  [(15, False), (16, False), (15, False), (17, False)],
        "right": [(15, True), (16, True), (15, True), (17, True)],
    },
}
# pokeemerald-expansion follower sheets: 32x32 frames: 0-1 down, 2-3 up, 4-5 left.
GEN3 = {
    "w": 32, "h": 32, "scale": SCALE,
    "cycles": {
        "down":  [(0, False), (1, False)],
        "up":    [(2, False), (3, False)],
        "left":  [(4, False), (5, False)],
        "right": [(4, True), (5, True)],
    },
}
FOLLOWERS = {           # name -> (sheet file, format)
    "Pikachu": ("pikachu.png", GEN3),
    "Flareon": ("flareon.png", GEN3),
    "Abra": ("abra.png", GEN3),
    "Lucario": ("lucario.png", GEN3),
    "Mew": ("mew.png", GEN3),
    "Snorlax": ("snorlax.png", GEN3),
    "Unown ?": ("unown_question.png", GEN3),
    "Jigglypuff": ("jigglypuff.png", GEN3),
    "Voltorb": ("voltorb.png", GEN3),
    "Gastly": ("gastly.png", GEN3),
    "Gengar": ("gengar.png", GEN3),
}
DEFAULT_FOLLOWER = "Pikachu"


def read_follower():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            name = f.read().strip()
    except OSError:
        return DEFAULT_FOLLOWER
    return name if name in FOLLOWERS else DEFAULT_FOLLOWER


def write_follower(name):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(name + "\n")
    os.replace(tmp, CONFIG)       # atomic: the running app never reads a half-written file


def lag_for(fmt):
    """Trail length so the follower walks one tile behind Red without overlapping him."""
    return ((SIZE + fmt["w"] * fmt["scale"]) // 2) // SPEED


def step(x, y, tx, ty, axis):
    """Walk 4-directionally toward (tx, ty). Returns (x, y, facing or None if standing, axis)."""
    dx, dy = tx - x, ty - y
    if math.hypot(dx, dy) <= KEEP_OFF:
        return x, y, None, axis
    if axis == "x" and abs(dy) > abs(dx) + AXIS_STICK:
        axis = "y"
    elif axis == "y" and abs(dx) > abs(dy) + AXIS_STICK:
        axis = "x"
    if axis == "x":
        if abs(dx) < 1:           # lined up on this axis: switch
            axis = "y"
        else:
            m = min(SPEED, abs(dx))
            return x + math.copysign(m, dx), y, "right" if dx > 0 else "left", axis
    m = min(SPEED, abs(dy))
    return x, y + math.copysign(m, dy), "down" if dy > 0 else "up", axis


def step_l(x, y, tx, ty, axis):
    """Like step(), but L-shaped: start along the longer axis, keep going until lined up
    with the pointer on it, then turn once. axis None = choose a fresh leg."""
    dx, dy = tx - x, ty - y
    if math.hypot(dx, dy) <= KEEP_OFF:
        return x, y, None, None                    # stopped: next walk picks a fresh L
    if axis is None:
        axis = "x" if abs(dx) >= abs(dy) else "y"
    if axis == "x" and abs(dx) < 1:
        axis = "y"
    elif axis == "y" and abs(dy) < 1:
        axis = "x"
    if axis == "x":
        m = min(SPEED, abs(dx))
        return x + math.copysign(m, dx), y, "right" if dx > 0 else "left", axis
    m = min(SPEED, abs(dy))
    return x, y + math.copysign(m, dy), "down" if dy > 0 else "up", axis


def run_state(running, dist):
    """Sprint once the pointer is far away; keep sprinting until it is close (hysteresis, no flicker)."""
    if dist > RUN_START:
        return True
    if dist < RUN_STOP:
        return False
    return running


def facing_of(dx, dy):
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


# --- Windows plumbing ---------------------------------------------------------------------------

def dpi_aware():
    """Use real pixels, so pointer and window coordinates agree on scaled (125 %, 150 %) displays."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # per-monitor
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def pointer_xy(root):
    """Mouse position in screen pixels. On Windows ask GetCursorPos directly: Tk's winfo_pointerxy
    uses the position saved with the last window message, which under Wine only updates while
    the mouse is over a Wine window (so the party froze in place)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        pt = wintypes.POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return pt.x, pt.y
    return root.winfo_pointerxy()


def click_through(win):
    """Let clicks pass through to the window underneath, keep it out of the taskbar and Alt+Tab."""
    if sys.platform != "win32":
        return
    import ctypes
    user32 = ctypes.windll.user32
    GWL_EXSTYLE = -20
    WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x00080000, 0x00000020
    WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x00000080, 0x08000000
    win.update_idletasks()
    hwnd = int(win.wm_frame(), 16)
    get = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    put = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
    get.restype = put.restype = ctypes.c_ssize_t
    get.argtypes = [ctypes.c_void_p, ctypes.c_int]
    put.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
    style = get(hwnd, GWL_EXSTYLE)
    put(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE)


def overlay_window(root, w, h):
    """Borderless, always-on-top, colour-keyed transparent, click-through window holding one label."""
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(bg=KEY)
    if sys.platform == "win32":
        win.attributes("-transparentcolor", KEY)
    label = tk.Label(win, bg=KEY, bd=0, highlightthickness=0, width=w, height=h)
    label.pack()
    win.geometry(f"{w}x{h}+0+0")
    click_through(win)
    return win, label


def frames_of(root, sheet_path, fw, fh, count, scale):
    """{(frame, mirrored): PhotoImage} scaled with nearest-neighbour (Tk zoom), crisp pixels."""
    sheet = tk.PhotoImage(master=root, file=sheet_path)
    out = {}
    for i in range(count):
        img = tk.PhotoImage(master=root)
        img.tk.call(img, "copy", sheet, "-from", i * fw, 0, (i + 1) * fw, fh, "-zoom", scale, scale)
        out[(i, False)] = img
        flipped = tk.PhotoImage(master=root)
        flipped.tk.call(flipped, "copy", img, "-subsample", -1, 1)    # negative subsample mirrors
        out[(i, True)] = flipped
    return out


def frame_count(fmt):
    return 1 + max(f for k in ("cycles", "run_cycles") for c in fmt.get(k, {}).values() for f, _ in c)


class Sprite:
    def __init__(self, root, sheet, fmt, x, y, facing):
        self.fmt = fmt
        self.w, self.h = fmt["w"] * fmt["scale"], fmt["h"] * fmt["scale"]
        self.frames = frames_of(root, os.path.join(ASSETS, sheet), fmt["w"], fmt["h"], frame_count(fmt), fmt["scale"])
        self.win, self.label = overlay_window(root, self.w, self.h)
        self.x, self.y, self.facing, self.walking, self.ticks = x, y, facing, False, 0
        self.running = False
        self.shown = None
        self.update(x, y, None)

    def update(self, x, y, facing, running=False, steps=1):
        """facing None = standing still. `steps` speeds the animation up while running."""
        self.walking = facing is not None
        self.running = running and self.walking
        if facing:
            self.facing = facing
        self.ticks = self.ticks + steps if self.walking else 0
        self.x, self.y = x, y
        self.win.geometry(f"+{int(self.x - self.w / 2)}+{int(self.y - self.h / 2)}")
        fmt = self.fmt
        cycle = fmt["run_cycles" if self.running and "run_cycles" in fmt else "cycles"][self.facing]
        key = cycle[(self.ticks // STEP_TICKS) % len(cycle)] if self.walking else cycle[0]
        if key != self.shown:                       # only touch Tk when the frame actually changes
            self.label.configure(image=self.frames[key])
            self.shown = key

    def raise_(self):
        self.win.lift()
        self.win.attributes("-topmost", True)

    def destroy(self):
        self.win.destroy()


class Dust:
    """One-shot dust puff: 3 frames of 16x8 stacked vertically, 8 game frames each (sAnim_GroundImpactDust)."""
    TICKS_PER_FRAME = 4             # 8 frames at 60 fps ~= 4 ticks at 33 fps

    def __init__(self, root, x, y):
        sheet = tk.PhotoImage(master=root, file=os.path.join(ASSETS, "dust.png"))
        self.frames = []
        for i in range(3):
            img = tk.PhotoImage(master=root)
            img.tk.call(img, "copy", sheet, "-from", 0, 8 * i, 16, 8 * (i + 1), "-zoom", SCALE, SCALE)
            self.frames.append(img)
        self.win, self.label = overlay_window(root, 16 * SCALE, 8 * SCALE)
        self.win.geometry(f"+{int(x - 8 * SCALE)}+{int(y - 8 * SCALE)}")   # (x, y) = feet: bottom-centre
        self.label.configure(image=self.frames[0])
        self.ticks = 0
        self.root = root
        root.after(1000 // FPS, self.tick)

    def tick(self):
        self.ticks += 1
        if self.ticks >= 3 * self.TICKS_PER_FRAME:
            self.win.destroy()
            return
        self.label.configure(image=self.frames[self.ticks // self.TICKS_PER_FRAME])
        self.root.after(1000 // FPS, self.tick)


class Party:
    def __init__(self, root):
        self.root = root
        px, py = pointer_xy(root)
        self.red = Sprite(root, "red.png", RED, float(px - 160), float(py + 120), "down")
        self.pika = None
        self.set_follower(read_follower())
        self.axis = "x"
        self.running = False
        self.config_mtime = self.mtime()
        root.after(CONFIG_POLL_MS, self.poll_config)
        root.after(1000 // FPS, self.tick)

    @staticmethod
    def mtime():
        try:
            return os.stat(CONFIG).st_mtime_ns
        except OSError:
            return None

    def poll_config(self):
        """Live switch when --settings saves a new choice (no inotify on Windows: cheap mtime poll)."""
        m = self.mtime()
        if m != self.config_mtime:
            self.config_mtime = m
            self.set_follower(read_follower())
        self.root.after(CONFIG_POLL_MS, self.poll_config)

    def set_follower(self, name):
        if self.pika and self.pika.name == name:
            return
        sheet, fmt = FOLLOWERS[name]
        lag = lag_for(fmt)
        rx, ry = self.red.x, self.red.y
        if self.pika:
            x, y, facing = self.pika.x, self.pika.y, self.pika.facing
            self.pika.destroy()
        else:
            x, y, facing = rx - lag * SPEED, ry, "right"
        # seed the trail on a straight line from the follower to Red so he walks to Red's heels
        self.trail = deque(((x + (rx - x) * i / lag, y + (ry - y) * i / lag) for i in range(lag + 1)),
                           maxlen=lag + 1)
        self.pika = Sprite(self.root, sheet, fmt, x, y, facing)
        self.pika.name = name
        self.red.raise_()
        self.red_on_top = True

    def tick(self):
        px, py = pointer_xy(self.root)
        was_running = self.running
        self.running = run_state(self.running, math.hypot(px - self.red.x, py - self.red.y))
        if DUST_PUFF and self.running and not was_running:
            Dust(self.root, self.red.x, self.red.y + self.red.h / 2)
            self.red.raise_()                       # puff goes behind Red, like a ground effect
            self.red_on_top = True
        # running = two walk steps per tick, so the trail (and the follower's distance) stays the same
        steps = 2 if self.running else 1
        x, y, facing = self.red.x, self.red.y, None
        for _ in range(steps):
            x, y, f, self.axis = (step_l if L_PATH else step)(x, y, px, py, self.axis)
            if f is None:
                break
            facing = f
            self.trail.append((x, y))
        self.red.update(x, y, facing, self.running, steps)
        if facing:
            nx, ny = self.trail[0]
            dx, dy = nx - self.pika.x, ny - self.pika.y
            self.pika.update(nx, ny, facing_of(dx, dy) if (dx or dy) else None, False, steps)
        else:
            self.pika.update(self.pika.x, self.pika.y, None)
        # whoever is lower on screen is drawn in front, as in the game
        red_front = self.red.y >= self.pika.y
        if red_front != self.red_on_top:
            (self.red if red_front else self.pika).raise_()
            self.red_on_top = red_front
        self.root.after(1000 // FPS, self.tick)


# --- single instance, quit ----------------------------------------------------------------------

def pid_alive(pid):
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(h)
    return code.value == 259                                          # STILL_ACTIVE


def running_pid():
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    return pid if pid != os.getpid() and pid_alive(pid) else None


def quit_running():
    pid = running_pid()
    if pid is None:
        print("Trainer Buddy is not running")
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        os.kill(pid, 15)
    try:
        os.remove(PIDFILE)
    except OSError:
        pass
    print("Trainer Buddy stopped")


# --- install ------------------------------------------------------------------------------------

def shortcut(path, target, args, workdir, icon=None):
    """Create a .lnk with WScript.Shell through PowerShell (-Command is not blocked by execution policy)."""
    q = lambda s: "'" + s.replace("'", "''") + "'"
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut({q(path)});"
          f"$s.TargetPath={q(target)};$s.Arguments={q(args)};$s.WorkingDirectory={q(workdir)};"
          + (f"$s.IconLocation={q(icon)};" if icon else "") + "$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], check=True)
    if not os.path.isfile(path):                    # e.g. a PowerShell stub that "succeeds" without doing it
        raise OSError(f"PowerShell did not create {path}")


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "TrainerBuddy"


def shortcut_paths():
    programs = os.path.join(APPDATA, "Microsoft", "Windows", "Start Menu", "Programs")
    return (os.path.join(programs, "Trainer Buddy.lnk"),
            os.path.join(programs, "Trainer Buddy Settings.lnk"))


def set_autostart(command):
    """Start with Windows via the per-user Run key (command None = remove). No admin rights needed."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as k:
        if command is None:
            try:
                winreg.DeleteValue(k, RUN_VALUE)
            except FileNotFoundError:
                pass
        else:
            winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, command)


def get_autostart():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, RUN_VALUE)[0]
    except FileNotFoundError:
        return None


def install():
    """Returns a short report. Exe: copies itself; script: copies the .pyw and sprites."""
    if sys.platform != "win32":
        sys.exit("--install is for Windows")
    os.makedirs(INSTALL_DIR, exist_ok=True)
    if FROZEN:
        exe = os.path.join(INSTALL_DIR, EXE_NAME)
        if os.path.normcase(sys.executable) != os.path.normcase(exe):
            shutil.copy2(sys.executable, exe)
        target, run_args = exe, ""
    else:
        if os.path.normcase(HERE) != os.path.normcase(INSTALL_DIR):
            shutil.copy2(os.path.abspath(__file__), os.path.join(INSTALL_DIR, "trainer_buddy.pyw"))
            shutil.copytree(ASSETS, os.path.join(INSTALL_DIR, "sprites"), dirs_exist_ok=True)
        target = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(target):
            target = sys.executable
        run_args = '"' + os.path.join(INSTALL_DIR, "trainer_buddy.pyw") + '"'
    set_autostart(f'"{target}" {run_args}'.strip())
    lines = [f"Installed to {INSTALL_DIR}", "Starts with Windows (registry: HKCU\\" + RUN_KEY + ")."]
    menu, settings_lnk = shortcut_paths()
    try:
        shortcut(menu, target, run_args, INSTALL_DIR)
        shortcut(settings_lnk, target, f"{run_args} --settings".strip(), INSTALL_DIR)
        lines.append("Start menu: Trainer Buddy, Trainer Buddy Settings.")
    except (OSError, subprocess.CalledProcessError) as e:     # PowerShell missing or blocked
        lines.append(f"Could not create Start menu entries ({e}). Run it with: \"{target}\" {run_args} [--settings]")
    report = "\n".join(lines)
    print(report)
    return report


def installed_exe():
    return os.path.join(INSTALL_DIR, EXE_NAME)


def offer_install():
    """Double-clicked exe that is not installed yet: ask once, install, run from the installed copy."""
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    yes = messagebox.askyesno(
        "Trainer Buddy",
        "Install Trainer Buddy?\n\nIt is copied to your user folder, starts with Windows and gets "
        "Start menu entries (Trainer Buddy, Trainer Buddy Settings).\n\nNo = just run it this once.",
        parent=root)
    report = install() if yes else None
    if report:
        messagebox.showinfo("Trainer Buddy", report + "\n\nStop it any time: TrainerBuddy.exe --quit "
                            "or end it in Task Manager. Remove: TrainerBuddy.exe --uninstall.", parent=root)
    root.destroy()
    if yes:
        subprocess.Popen([installed_exe()], close_fds=True)
    return yes


def uninstall():
    quit_running()
    if sys.platform == "win32":
        set_autostart(None)
    for p in shortcut_paths():
        try:
            os.remove(p)
        except OSError:
            pass
    if FROZEN and os.path.normcase(HERE) == os.path.normcase(INSTALL_DIR):
        # a running exe can't delete itself: cmd retries for up to ~30 s until this process
        # (and the onefile launcher that holds the .exe open) has exited
        d = INSTALL_DIR
        subprocess.Popen(f'cmd /c for /l %i in (1,1,30) do @(if exist "{d}" (ping -n 2 127.0.0.1 >nul '
                         f'& rmdir /s /q "{d}" 2>nul))',
                         creationflags=0x08000000, close_fds=True)          # CREATE_NO_WINDOW
    else:
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    print(f"Removed shortcuts and {INSTALL_DIR} (your Pokemon choice in {os.path.dirname(CONFIG)} is kept)")


# --- settings window ----------------------------------------------------------------------------

def settings():
    """Small window to pick the follower; the running buddy switches as soon as it is saved."""
    dpi_aware()
    root = tk.Tk()
    root.title("Trainer Buddy")
    root.resizable(False, False)
    frame = tk.Frame(root, padx=12, pady=12)
    frame.pack()
    tk.Label(frame, text="Pokémon following Red:", anchor="w").pack(fill="x", pady=(0, 6))
    choice = tk.StringVar(master=root, value=read_follower())
    icons = []                      # keep references, or Tk drops the images
    for name, (sheet, fmt) in FOLLOWERS.items():
        full = tk.PhotoImage(master=root, file=os.path.join(ASSETS, sheet))
        big = tk.PhotoImage(master=root)        # 48 px tall like the Linux version: zoom 3, subsample 2
        big.tk.call(big, "copy", full, "-from", 0, 0, fmt["w"], fmt["h"], "-zoom", 3, 3)
        icon = tk.PhotoImage(master=root)
        icon.tk.call(icon, "copy", big, "-subsample", 2, 2)
        icons.append(icon)
        tk.Radiobutton(frame, text="  " + name, image=icon, compound="left", variable=choice, value=name,
                       anchor="w", command=lambda: write_follower(choice.get())).pack(fill="x")
    tk.Button(frame, text="Close", width=12, command=root.destroy).pack(pady=(10, 0))
    root.mainloop()


# --- self-test ----------------------------------------------------------------------------------

def selftest():
    assert step(0, 0, 10, 10, "x")[2] is None                         # inside keep-off: stand
    x, y, f, a = step(0, 0, 200, 50, "x")
    assert (x, y, f, a) == (SPEED, 0, "right", "x")                    # walks along dominant axis
    assert step(0, 0, 50, 55, "x")[2] == "right"                       # small lead: no turn yet
    assert step(0, 0, 50, 100, "x")[2:] == ("down", "y")               # clear lead: turns
    assert step(0, 0, 0.5, -100, "x")[2:] == ("up", "y")               # lined up: switches axis
    assert step(0, 0, -100, 0, "x")[0] == -SPEED
    # L path: a diagonal is walked as one straight leg then one turn, never a zig-zag
    x, y, axis, faces = 0.0, 0.0, None, []
    while True:
        x, y, f, axis = step_l(x, y, 200, 150, axis)
        if f is None:
            break
        if not faces or faces[-1] != f:
            faces.append(f)
    assert faces == ["right", "down"], faces
    assert x == 200                                                    # first leg finished before turning
    assert step_l(0, 0, 50, 300, None)[2] == "down"                    # longer axis first
    assert run_state(False, RUN_START + 1) and not run_state(False, RUN_START - 1)
    assert run_state(True, RUN_STOP + 1) and not run_state(True, RUN_STOP - 1)   # keeps running until close
    assert [facing_of(*d) for d in ((4, 0), (-4, 0), (0, 4), (0, -4))] == ["right", "left", "down", "up"]
    # the follower (trail[0]) stays exactly LAG steps behind along Red's path, around a corner
    lag = lag_for(RED)
    assert lag == SIZE // SPEED
    trail = deque(((i * SPEED - lag * SPEED, 0) for i in range(lag + 1)), maxlen=lag + 1)
    x, y = 0, 0
    for _ in range(lag):
        y += SPEED
        trail.append((x, y))
    assert trail[0] == (0, 0) and trail[-1] == (0, lag * SPEED)
    assert lag_for(GEN3) > lag                                        # bigger sprite walks further back
    root = tk.Tk()
    root.withdraw()
    dust = tk.PhotoImage(master=root, file=os.path.join(ASSETS, "dust.png"))
    assert (dust.width(), dust.height()) == (16, 24)                  # 3 frames of 16x8
    for name, (sheet, fmt) in [("Red", ("red.png", RED))] + list(FOLLOWERS.items()):
        img = tk.PhotoImage(master=root, file=os.path.join(ASSETS, sheet))   # every sheet fits its format
        assert (img.width(), img.height()) == (fmt["w"] * frame_count(fmt), fmt["h"]), name
    frames = frames_of(root, os.path.join(ASSETS, "red.png"), 16, 32, 3, SCALE)
    a, b = frames[(2, False)], frames[(2, True)]
    assert (a.width(), a.height()) == (16 * SCALE, 32 * SCALE)
    w = a.width()
    assert all(a.get(x, y) == b.get(w - 1 - x, y) for x in range(0, w, 3) for y in range(0, 64, 3))   # mirrored
    root.destroy()
    global CONFIG
    real, CONFIG = CONFIG, os.path.join(os.environ.get("TEMP", "/tmp"), f"trainer-buddy-test-{os.getpid()}", "follower")
    try:
        assert read_follower() == DEFAULT_FOLLOWER                    # no file yet
        write_follower("Mew")
        assert read_follower() == "Mew"
        write_follower("Missingno")
        assert read_follower() == DEFAULT_FOLLOWER                    # unknown name falls back
    finally:
        if os.path.exists(CONFIG):
            os.remove(CONFIG)
        os.rmdir(os.path.dirname(CONFIG))
        CONFIG = real
    print("selftest ok")


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        if not FROZEN:
            return selftest()
        # the exe has no console: report through the exit code and a log file instead
        import traceback
        log = os.path.join(os.environ.get("TEMP", HERE), "trainer-buddy-selftest.txt")
        try:
            selftest()
        except BaseException:
            with open(log, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
            sys.exit(1)
        with open(log, "w", encoding="utf-8") as f:
            f.write("selftest ok\n")
        return
    if "--settings" in args:
        return settings()
    if "--install" in args:
        return install()
    if "--uninstall" in args:
        return uninstall()
    if "--quit" in args:
        return quit_running()
    if running_pid() is not None:                   # already running: don't start a second party
        return
    if (FROZEN and sys.platform == "win32" and not args
            and os.path.normcase(sys.executable) != os.path.normcase(installed_exe())
            and not os.path.isfile(installed_exe())):
        if offer_install():                         # the installed copy takes over
            return
    os.makedirs(os.path.dirname(PIDFILE), exist_ok=True)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    dpi_aware()
    root = tk.Tk()
    root.withdraw()                                 # only the sprite windows are shown
    Party(root)
    try:
        root.mainloop()
    finally:
        try:
            os.remove(PIDFILE)
        except OSError:
            pass


if __name__ == "__main__":
    main()
