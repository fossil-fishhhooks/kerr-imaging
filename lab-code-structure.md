## Project Structure

```
project/
├── main.py              # Qt main window — assembles panels
├── main.ui              # Qt main window layout
├── instrument_a/        # one folder per instrument / subsystem
│   ├── instrument_name.py        # low-level USB/serial/DLL wrapper
│   ├── helper.py        # pure functions, no class needed
│   └── panel.py         # QWidget that goes in main window
├── instrument_b/
│   ├── instrument_b.py
│   └── panel.py
├── instrument_c/        # example for instruments where we program our own firmware
│   ├── firmware
│   │   ├── main.c
│   │   └── config.txt
│   └── update_instrument_c.py   # compiles & flashes firmware
├── test/                # standalone diagnostic scripts
│   └── probe_driver.py 
├── libcamera.dll
└── config.txt           # config for dlls, etc
```

## The main file

A single Qt main-window script (`main.py`/`main_des.py`) that creates each instrument's panel and arranges them in a layout. It owns the top-level timer, connects cross-instrument signals (e.g. "when camera exposure changes, tell DLP to update"), and handles status/logging. It should not contain instrument logic — only orchestration and UI layout.

## One folder per instrument

Each physical device or subsystem gets its own folder. Inside:

A main file — wraps the hardware communication (USB, serial, DLL, MMIO). It lives in a class that exposes the device's high-level operations. It should have a safe destructor! It should have an `if __name__ == "__main__"` block that self-tests the driver standalone (probe registers, read status, set values, verify readback). This lets you test hardware without launching the GUI.

**Helper files** (e.g. `math.py`, `conversions.py`) — just functions and constants. No class needed. Imported by the driver or panel.

**`panel.py`** — a `QWidget` (or `QGroupBox`) that will be embedded in `main.py`.
- Owns its own layout, controls (sliders, spinners, buttons), and a `QTimer` for debouncing / polling.
- Manages its own connect/disconnect lifecycle. Does NOT access hardware until connected.
- Emits `QtCore.pyqtSignal` for status changes so `main.py` can react (e.g. update a toolbar label).
- Contains NO device-specific hardware logic — it calls `driver.py` methods only.
- Contains NO file parsing, calibration math, or data processing. Those go in helper files or the driver.

**Subfolders** — to be used when a subsystem needs sub-subsystems (eg `camera` and `camera/processing` and `camera/calibration`).

## The `test/` folder

Standalone scripts you run by hand to probe or debug a device. They:
- Import the driver directly, or contain a stripped-down version of it
- Do not import the panel or main window
- Are safe to run with no GUI
- Output to the terminal or save files (plots, CSVs)
- Naming: should contain the name of the instrument/module/subsystem it aims to test

## `__init__.py`

Each instrument folder's `__init__.py` exports the class(es) from the driver but **NOT the panel.**

```
from .instrument import MyInstrument
__all__ = ["MyInstrument"]
```

## `if __name__ == "__main__"` in driver files

Every instrument interface file should have one. It opens the device, runs a few operations, prints results, and closes. This serves as both a smoke test and documentation of basic usage. It should work without any GUI or other modules (import only stdlib + the DLL).

## Conventions
- Abbreviation is good, but dont make things unreadable.
- Allow code to work despite missing instruments. This doesnt mean functional, but rather avoiding an abrupt crash of the whole UI.
- Avoid hardcoding instrument ports. Using defaults is fine.
- Avoid hardcoding lib paths, unless, of course, Windows decides you have to.
- Avoid OS-specific code! Except: Instrument drivers are ok to be left as .dll's
- Don't block the UI.
- ***Avoid silent-fails!!!***
- .gitignore is good. Use it. Don't hand people your `__pycache__` every time! Also use it to avoid stuffing large .dll's and other binaries on github.
- Magic numbers are OK **as long as its obvious what they do.** Multiplying an output by 9.86960440109 is bad (its pi^2); time.sleep(0.5) is perfectly fine.
