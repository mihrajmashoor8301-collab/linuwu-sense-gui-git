#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import json
import socket
import pathlib
import shutil
import subprocess
import time

BASE = "/sys/devices/platform/acer-wmi"
PS = BASE + "/predator_sense"
PROFILE = BASE + "/platform-profile/platform-profile-0"
FAN = PS + "/fan_speed"
BAT = PS + "/battery_limiter"
USB = PS + "/usb_charging"
PROFILE_SOCKET = "/run/predsenselinux-profile-helper/profile.sock"
PROFILES = ("low-power", "quiet", "balanced", "balanced-performance", "performance")
HWMON = pathlib.Path("/sys/class/hwmon")
NVIDIA_SMI = shutil.which("nvidia-smi")
_gpu_temp = "N/A"
_gpu_temp_updated = 0.0

def read(p, default="N/A"):
    try:
        with open(p) as f: return f.read().strip()
    except Exception:
        return default

def hwmon_read(chip, attribute, default="N/A"):
    try:
        for device in HWMON.glob("hwmon*"):
            if (device / "name").read_text().strip() == chip:
                return (device / attribute).read_text().strip()
    except (OSError, ValueError):
        pass
    return default

def cpu_temperature():
    try:
        for device in HWMON.glob("hwmon*"):
            if (device / "name").read_text().strip() != "coretemp":
                continue
            for label in device.glob("temp*_label"):
                if label.read_text().strip().lower() == "package id 0":
                    raw = (device / label.name.replace("_label", "_input")).read_text().strip()
                    return f"{int(raw) / 1000:.1f}°C"
    except (OSError, ValueError):
        pass
    return "N/A"

def gpu_temperature():
    global _gpu_temp, _gpu_temp_updated
    now = time.monotonic()
    if now - _gpu_temp_updated >= 3:
        _gpu_temp_updated = now
        if NVIDIA_SMI:
            try:
                result = subprocess.run(
                    [NVIDIA_SMI, "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                    check=True, capture_output=True, text=True, timeout=2,
                )
                value = result.stdout.strip().splitlines()[0].strip()
                _gpu_temp = f"{int(value)}°C"
            except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                _gpu_temp = "N/A"
        else:
            _gpu_temp = "N/A"
    return _gpu_temp
def write(p, v):
    try:
        with open(p, "w") as f: f.write(str(v))
        return True
    except Exception as e:
        messagebox.showerror("PredSenseLinux", f"Write failed:\n{p}\n\n{e}")
        return False
def fans(_=None):
    a, b = cpu.get(), gpu.get()
    write(FAN, f"{int(a)},{int(b)}")
    fan_text.set(f"CPU Fan {int(a)}%   •   GPU Fan {int(b)}%")
def profile(p):
    if p not in PROFILES:
        messagebox.showerror("PredSenseLinux", "Unknown performance profile.")
        return
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(PROFILE_SOCKET)
            client.sendall((json.dumps({"action": "set_profile", "profile": p}) + "\n").encode("utf-8"))
            response = json.loads(client.makefile("rb").readline(1024))
        if response.get("ok"):
            prof.set(p)
        else:
            messagebox.showerror("PredSenseLinux", response.get("error", "Profile change failed."))
    except Exception as e:
        messagebox.showerror("PredSenseLinux", f"Profile helper unavailable:\n{e}")
def refresh():
    rpm.set(f"CPU Fan: {hwmon_read('acer', 'fan1_input')} RPM    •    GPU Fan: {hwmon_read('acer', 'fan2_input')} RPM")
    temps.set(f"CPU: {cpu_temperature()}    •    GPU: {gpu_temperature()}")
    prof.set(read(PROFILE + "/profile", "unknown"))
    root.after(1000, refresh)
root = tk.Tk()
root.title("PredSenseLinux")
root.geometry("560x475")
root.resizable(False, False)

ttk.Label(root, text="PredSenseLinux", font=("TkDefaultFont", 24, "bold")).pack(pady=(18, 2))
ttk.Label(root, text="Acer Predator Fan & Performance Control").pack()
rpm = tk.StringVar()
ttk.Label(root, textvariable=rpm, font=("TkDefaultFont", 13, "bold")).pack(pady=14)
temps = tk.StringVar(value="CPU: N/A    •    GPU: N/A")
ttk.Label(root, textvariable=temps, font=("TkDefaultFont", 11)).pack(pady=(0, 12))

f = ttk.LabelFrame(root, text="Manual Fan Control", padding=14)
f.pack(fill="x", padx=20)

cpu = tk.IntVar(value=50)
gpu = tk.IntVar(value=50)
fan_text = tk.StringVar(value="CPU Fan 50%   •   GPU Fan 50%")
ttk.Label(f, text="CPU Fan").grid(row=0, column=0, sticky="w")
ttk.Scale(f, from_=1, to=100, variable=cpu, command=fans).grid(row=0, column=1, sticky="ew", padx=10)
ttk.Label(f, textvariable=cpu, width=4).grid(row=0, column=2)
ttk.Label(f, text="GPU Fan").grid(row=1, column=0, sticky="w")
ttk.Scale(f, from_=1, to=100, variable=gpu, command=fans).grid(row=1, column=1, sticky="ew", padx=10)
ttk.Label(f, textvariable=gpu, width=4).grid(row=1, column=2)
ttk.Label(f, textvariable=fan_text).grid(row=2, column=0, columnspan=3, pady=(8, 0))
f.columnconfigure(1, weight=1)

p = ttk.LabelFrame(root, text="Performance Profile", padding=12)
p.pack(fill="x", padx=20, pady=12)
prof = tk.StringVar(value=read(PROFILE + "/profile", "balanced"))
for i, x in enumerate(PROFILES):
    ttk.Button(p, text=x.title(), command=lambda x=x: profile(x)).grid(row=0, column=i, padx=3, sticky="ew")
p.columnconfigure(i, weight=1)

c = ttk.Frame(root)
c.pack(fill="x", padx=20, pady=4)
bat = tk.BooleanVar(value=read(BAT, "0") == "1")
usb = tk.IntVar(value=int(read(USB, "30")) if read(USB, "30").isdigit() else 30)
ttk.Checkbutton(c, text="Battery Limiter", variable=bat, command=lambda: write(BAT, "1" if bat.get() else "0")).grid(row=0, column=0, padx=8)
ttk.Label(c, text="USB Charging").grid(row=0, column=1, padx=(20, 5))
ttk.Spinbox(c, from_=0, to=100, textvariable=usb, width=6, command=lambda: write(USB, usb.get())).grid(row=0, column=2)
ttk.Button(c, text="Apply", command=lambda: write(USB, usb.get())).grid(row=0, column=3, padx=5)

ttk.Label(root, text="Controls use the installed Predator Linux kernel interface.", foreground="gray").pack(pady=14)
refresh()
root.mainloop()
