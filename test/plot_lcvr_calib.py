"""Plot retardance-vs-voltage curves for one LCVR at different wavelengths."""

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
    deltac = abs(nm_633[-1])  # absolute nm at highest voltage (~20 V)
    nm_new = np.array([calculate_correct_delta2(NATIVE_WL, n, target_wl, deltac) for n in nm_633])
    waves_new = nm_new / target_wl
    return mv, nm_new, waves_new

MODEL = "H15230"
WAVELENGTHS = [405, 488, 532, 633, 780, 850, 1064]

raw = load_raw_mv_nm(MODEL)
mv_raw = raw[:, 0]
nm_raw = raw[:, 1]
waves_raw = nm_raw / NATIVE_WL

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(f"LCVR Calibration — {MODEL}")

colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(WAVELENGTHS)))

for wl, c in zip(WAVELENGTHS, colors):
    mv, nm, waves = shift_calibration(raw, wl)
    label = f"{wl} nm"
    ax1.plot(mv, waves, color=c, label=label, linewidth=1.5)
    ax2.plot(mv, nm, color=c, label=label, linewidth=1.5)

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

plt.tight_layout()
out = os.path.join(os.path.dirname(__file__), f"{MODEL}_wavelength_shift.png")
plt.savefig(out, dpi=150)
print(f"Saved: {out}")
# uncomment to show interactively: plt.show()
