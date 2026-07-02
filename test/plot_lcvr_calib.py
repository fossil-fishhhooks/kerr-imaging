"""Plot retardance-vs-voltage curves for LCVRs at various wavelengths."""

import os
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lcvr.i_suck_at_math import calculate_correct_delta2

CALIB_DIR = os.path.join(os.path.dirname(__file__), "..", "lcvr", "calib")
NATIVE_WL = 633.0

def load_raw_mv_nm(model):
    path = os.path.join(CALIB_DIR, model)
    raw = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                mv = float(parts[0])
                nm = float(parts[1])
                raw.append((mv, nm))
    return np.array(sorted(raw, key=lambda p: p[0]))

def shift_calibration(raw, target_wl):
    mv = raw[:, 0]
    nm_633 = raw[:, 1]
    deltac = abs(nm_633[-1])
    nm_new = np.array([calculate_correct_delta2(NATIVE_WL, n, target_wl, deltac) for n in nm_633])
    waves_new = nm_new / target_wl
    return mv, nm_new, waves_new

# ── Figure 1: broad spectrum comparison ──────────────────────────────────

MODEL = "H15230"
WAVELENGTHS = [405, 488, 532, 633, 780, 850, 1064]

raw = load_raw_mv_nm(MODEL)

fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig1.suptitle(f"LCVR Calibration — {MODEL}")

colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(WAVELENGTHS)))

for wl, c in zip(WAVELENGTHS, colors):
    mv, nm, waves = shift_calibration(raw, wl)
    ax1.plot(mv, waves, color=c, label=f"{wl} nm", linewidth=1.5)
    ax2.plot(mv, nm, color=c, label=f"{wl} nm", linewidth=1.5)

ax1.set_xlabel("Voltage (mV)")
ax1.set_ylabel("Retardance (waves)")
ax1.set_title("Retardance vs Voltage (in waves)")
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)

ax2.set_xlabel("Voltage (mV)")
ax2.set_ylabel("Retardance (nm)")
ax2.set_title("Retardance vs Voltage (in nm)")
ax2.legend(fontsize=8)
ax2.grid(True, alpha=0.3)

fig1.tight_layout()
out1 = os.path.join(os.path.dirname(__file__), f"{MODEL}_wavelength_shift.png")
fig1.savefig(out1, dpi=150)
print(f"Saved: {out1}")

# ── Figures 2 & 3: RGB LED bands (stock EVM optical engine), one per LCVR

LEDS = [
    ("Red",   617, 609, 624, "#e00000"),
    ("Green", 570, 565, 575, "#00c000"),
    ("Blue",  459, 450, 480, "#0040ff"),
]

for model in ("H15230", "H15231"):
    raw = load_raw_mv_nm(model)
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(f"{model} — DLP EVM LED wavelengths")

    for name, center, lo, hi, base_color in LEDS:
        mv_c, nm_c, waves_c = shift_calibration(raw, center)
        mv_l, nm_l, waves_l = shift_calibration(raw, lo)
        mv_h, nm_h, waves_h = shift_calibration(raw, hi)

        ax.plot(mv_c, waves_c, color=base_color, linewidth=2,
                label=f"{name} {center} nm ({lo}–{hi})")
        ax.plot(mv_l, waves_l, color=base_color, linestyle="--",
                linewidth=1, alpha=0.5)
        ax.plot(mv_h, waves_h, color=base_color, linestyle="--",
                linewidth=1, alpha=0.5)

    ax.set_xlabel("Voltage (mV)")
    ax.set_ylabel("Retardance (waves)")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    out = os.path.join(os.path.dirname(__file__), f"{model}_LED_bands.png")
    fig.savefig(out, dpi=150)
    print(f"Saved: {out}")
