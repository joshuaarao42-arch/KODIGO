# KODIGO — QR Code Studio

**Create. Customize. Connect.**

KODIGO is a customizable QR Code Studio with a Windows desktop application and a web version deployable to Vercel. Create QR codes for links, text, contact cards, and Wi-Fi; personalize their appearance; preview them; and export high-quality PNG images.

## Web app

- Link, plain text, vCard contact, and Wi-Fi QR generation.
- Live QR preview and PNG export.
- Foreground/background colors, six color presets, and contrast guidance.
- Square, rounded, and dot module styles.
- Center logo uploads, logo sizing, and quiet-zone controls.
- Standard, High, and Ultra export quality.
- Browser-local QR history.
- KODIGO AI assistant powered by the Gemini Developer API free tier.

## Deploy to Vercel

1. Import **joshuaarao42-arch/KODIGO** into Vercel (the project is linked already if you used the existing KODIGO Vercel project).
2. Keep the project root directory set to the repository root.
3. Add the environment variable below in **Project Settings → Environment Variables**:

| Name | Value |
|---|---|
| GEMINI_API_KEY | Your Gemini API key from https://aistudio.google.com/app/apikey |

4. Enable the variable for Production and Preview, then redeploy.

The AI assistant uses the Gemini 3.5 Flash-Lite model. The Gemini Developer API free tier has usage limits and model availability can change. The API key is read only by the server; never put it in browser code or commit it to GitHub. QR generation works even when the key is not configured, but the AI assistant will be unavailable.

## Web architecture

- Flask app deployed through Vercel's native Python/Flask support.
- Existing KODIGO/payloads.py and KODIGO/qr_engine.py are reused for QR payload construction and image rendering.
- Static assets are served from the public directory.
- Browser history is stored locally in the current browser using localStorage; it is not synced between devices.
- Uploaded center logos are processed temporarily and are not retained as account files.
- No account or database is required for the web version.

## Desktop application

The original CustomTkinter desktop application remains available. Its local SQLite history and Windows executable workflow are unchanged.

### Desktop features

- **Multiple QR Types** — URLs, plain text, contact cards (vCards), and Wi-Fi credentials.
- **Live Preview** — See the QR code update as you modify its content and appearance.
- **Customizable Designs** — Personalize QR colors, module shapes, and add custom center logos.
- **High-Quality Export** — Export PNG images in Standard, High, or Ultra resolution with 300 DPI metadata.
- **QR Code History** — Search, reopen, export, and delete previously generated QR codes.
- **Light & Dark Themes** — Switch between application themes.
- **Readability Protection** — Contrast checking and automatic high error correction when adding logos.

## Preview

![KODIGO desktop preview](https://github.com/joshuaarao42-arch/KODIGO/blob/main/IMAGES%20(KODIGO)/Screenshot%202026-10-31%20134800.png?raw=true)
![KODIGO desktop preview](https://github.com/joshuaarao42-arch/KODIGO/blob/main/IMAGES%20(KODIGO)/Screenshot%202026-10-31%20134819.png?raw=true)

## Built with

| Technology | Purpose |
|---|---|
| Python | Core application and API |
| CustomTkinter | Desktop interface |
| Flask | Vercel web application |
| qrcode | QR generation |
| Pillow | Image rendering and processing |
| SQLite | Desktop QR history |
| Browser localStorage | Web QR history |
| Gemini Developer API | KODIGO AI assistant |
| Vercel | Web deployment |

## Run the desktop application locally

Requirements: Python 3.10 or newer.

    git clone https://github.com/joshuaarao42-arch/KODIGO.git
    cd KODIGO
    py -m venv .venv
    .\.venv\Scripts\activate
    python -m pip install -r requirements-desktop.txt
    python main.py

## Run the web application locally

    python -m pip install -r requirements.txt
    python -m flask --app app run --debug

Open http://127.0.0.1:5000. To enable the AI assistant locally, set GEMINI_API_KEY in your shell before starting Flask.

## Build the Windows application

Run build_exe.bat. The executable is created at dist/KODIGO/KODIGO.exe.

## Keyboard shortcut

| Shortcut | Action |
|---|---|
| Ctrl + S | Export current QR code (desktop app) |

## Project structure

    KODIGO/
    ├── app.py
    ├── api/
    │   └── index.py
    ├── public/
    │   ├── app.js
    │   ├── styles.css
    │   └── favicon.svg
    ├── templates/
    │   └── index.html
    ├── KODIGO/
    │   ├── app.py
    │   ├── config.py
    │   ├── database.py
    │   ├── payloads.py
    │   ├── qr_engine.py
    │   └── ui/
    ├── main.py
    ├── requirements.txt
    ├── requirements-desktop.txt
    └── README.md

## Data & privacy

The desktop version stores QR history locally in SQLite. The web version stores saved QR images in the current browser only. Browser history is not an account backup or cloud sync. Wi-Fi QR codes encode network credentials, so treat exported images as sensitive.

## Contributing

Contributions are welcome. Please read CONTRIBUTING.md, test affected workflows, and never commit API keys, real Wi-Fi credentials, or private contact information.

## Author

**Joshua C. Arao** — Computer Science student at the University of Science and Technology of Southern Philippines (USTP).

## License

MIT License. See LICENSE.
