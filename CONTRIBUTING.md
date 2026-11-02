# Contributing to KODIGO — QR Code Studio

Thank you for contributing to KODIGO, a Python desktop studio for generating, customizing, previewing, and exporting QR codes.

## Getting started (Windows)

```bash
git clone https://github.com/joshuaarao42-arch/KODIGO.git
cd KODIGO
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Activate the virtual environment if preferred. Follow the README if the supported entry point or setup steps change.

## What you can contribute

- QR generation for URLs, text, vCards, and Wi-Fi details.
- Live preview, colors, module shapes, and center-logo handling.
- PNG export quality, resolution, and metadata.
- Search, history, reopening, and deletion of saved QR entries.
- Theme consistency, accessibility, and Windows packaging.

## Project-specific guidelines

When changing generation or styling, scan test codes with more than one QR reader. Preserve adequate contrast and error-correction safeguards, especially when adding center logos. Verify export dimensions and file readability at each supported quality level. Treat Wi-Fi credentials and contact information as sensitive; never commit real examples or saved history databases.

## Development standards

Follow existing Python and UI conventions. Keep QR generation, preview, and export behavior consistent. Validate user-provided content and file paths. Do not silently overwrite an existing export or source file. Document new dependencies and packaging changes.

## Testing your changes

Run KODIGO and test the affected QR types, preview settings, history actions, and export options. Scan generated codes using multiple readers. Test invalid or empty content and confirm errors are understandable. Include screenshots for interface changes.

## Branch and commit workflow

Use a focused branch such as `feature/vcard-fields`, `fix/logo-scan-reliability`, or `docs/windows-setup`. Use commit prefixes such as `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, and `test:`.

## Opening a pull request

Include the QR content type, settings used, output format, scan results, and test steps. Add screenshots for interface changes and explain any compatibility or packaging impact.

## Reporting issues

Include Windows version, Python version, reproduction steps, expected and actual behavior, and sanitized error messages. Never post real Wi-Fi passwords, private contact details, or QR history files.

## Code of conduct

Be respectful and constructive. Give actionable feedback and help keep contributions safe, accessible, and reliable.
