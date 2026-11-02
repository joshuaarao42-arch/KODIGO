# Contributing to KODIGO — QR Code Studio

KODIGO is a Python desktop studio for generating, customizing, previewing, and exporting QR codes.

## Clone and run (Windows)
```bash
git clone https://github.com/joshuaarao42-arch/KODIGO.git
cd KODIGO
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Project-specific contributions
- QR types: URLs, text, vCards, and Wi-Fi credentials.
- Live preview, colors, module shapes, and center logos.
- PNG export resolution, quality, and metadata.
- QR history, search, reopen, export, and delete.
- Theme consistency and Windows executable packaging.

## QR reliability and privacy
When changing generation or styling, scan test codes with more than one QR reader. Preserve contrast and error-correction safeguards, especially with center logos. Test exported files at each quality level. Treat Wi-Fi credentials and contact details as sensitive; never commit real examples or history databases.

Use branches such as `feature/vcard-fields` or `fix/logo-scan-reliability`. Include sample payloads, export settings, and scan results in pull requests.
