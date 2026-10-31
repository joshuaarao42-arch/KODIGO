# KODIGO — QR Code Studio

Create polished, customizable QR codes from a simple desktop app. KODIGO supports links, plain text, contact cards, and Wi-Fi credentials, with a live preview and PNG export.

## Features

- **Four QR types:** URLs, text, vCards, and Wi-Fi network credentials
- **Live preview:** see changes as you edit your content or style
- **Personalized appearance:** choose colors, module shapes, and an optional center logo
- **Readable output:** contrast checking and automatic high error correction when a logo is used
- **High quality PNGs:** export at Standard, High, or Ultra resolution with 300 DPI metadata
- **Saved history:** search previous codes, reopen them, export again, or delete them
- **Light and dark themes:** switch the app appearance from the sidebar

## Preview

> Add a screenshot of the app here when one is available.

## Requirements

- Python 3
- Windows for the included `.exe` build script

## Run from source

Open PowerShell in this folder and create a virtual environment:

```powershell
py -m venv .venv
```

Install dependencies and start the app:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

If the `py` command is unavailable, install Python from [python.org](https://www.python.org/downloads/) and reopen PowerShell.

### Optional: use uv

If [uv](https://docs.astral.sh/uv/) is installed and can access the network:

```powershell
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv run --python .venv\Scripts\python.exe main.py
```

## Build the Windows app

With Python installed, run `build_exe.bat` from this folder. The script installs the requirements and PyInstaller, generates the app icon, and builds the executable. The output is:

```text
dist/KODIGO/KODIGO.exe
```

## Keyboard shortcut

| Shortcut | Action |
| --- | --- |
| `Ctrl+S` | Export the current QR code |

## Data and privacy

QR history is stored locally in SQLite at `%APPDATA%\KODIGO\history.db` on Windows. The app does not need an account or a hosted service to create QR codes.

## Project structure

```text
main.py                 Application entry point
make_icon.py            Generates the Windows application icon
build_exe.bat           Builds the Windows executable
requirements.txt        Python package requirements
KODIGO/
  app.py                Main window and navigation
  config.py             App settings and user data paths
  database.py           Local SQLite history
  payloads.py           URL, text, vCard, and Wi-Fi payloads
  qr_engine.py          QR generation, styling, and PNG export
  ui/                   Screens, forms, widgets, and theme
```

## Dependencies

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — desktop interface
- [qrcode](https://github.com/lincolnloop/python-qrcode) — QR code generation
- [Pillow](https://python-pillow.org/) — image processing and export

