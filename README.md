# KODIGO — QR Code Studio

**Create. Customize. Connect.**

KODIGO is a customizable QR Code Studio built with Python. It allows users to generate, personalize, preview, and export QR codes through a modern desktop application.

Designed with a clean interface and intuitive controls, KODIGO makes QR code creation simple and convenient.

## ✨ Features

- **Multiple QR Types** — Generate QR codes for URLs, plain text, contact cards (vCards), and Wi-Fi credentials.
- **Live Preview** — See your QR code update as you modify its content and appearance.
- **Customizable Designs** — Personalize QR colors, module shapes, and add custom center logos.
- **High-Quality Export** — Export QR codes as PNG images in Standard, High, or Ultra resolution with 300 DPI metadata.
- **QR Code History** — Search, reopen, export, and delete previously generated QR codes.
- **Light & Dark Themes** — Switch between application themes to suit your preference.
- **Readability Protection** — Contrast checking and automatic high error correction when adding logos.

## 🖥️ Preview

![image alt](https://github.com/joshuaarao42-arch/KODIGO/blob/main/IMAGES%20(KODIGO)/Screenshot%202026-10-31%20134800.png?raw=true)
![image alt](https://github.com/joshuaarao42-arch/KODIGO/blob/main/IMAGES%20(KODIGO)/Screenshot%202026-10-31%20134819.png?raw=true)

## 🛠️ Built With

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| CustomTkinter | Desktop graphical interface |
| qrcode | QR code generation |
| Pillow (PIL) | Image processing |
| SQLite | Local QR code history |
| PyInstaller | Windows executable packaging |

## 📦 Installation

### Requirements

- Python 3
- Windows (for the included executable build script)

### 1. Clone the Repository

```bash
git clone https://github.com/joshuaarao42-arch/KODIGO.git
```

### 2. Navigate to the Project Directory

```bash
cd KODIGO
```

### 3. Create a Virtual Environment

```bash
py -m venv .venv
```

### 4. Install Dependencies

```bash
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 5. Run the Application

```bash
.\.venv\Scripts\python.exe main.py
```

## 🏗️ Build as a Windows Application

KODIGO can be packaged into a standalone Windows application using the included build script.

Run:

```bash
build_exe.bat
```

Once the build process is complete, the executable will be available at:

```text
dist/KODIGO/KODIGO.exe
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl + S` | Export current QR code |

## 📁 Project Structure

```text
KODIGO/
│
├── KODIGO/
│   ├── app.py
│   ├── config.py
│   ├── database.py
│   ├── payloads.py
│   ├── qr_engine.py
│   │
│   └── ui/
│       ├── Screens
│       ├── Forms
│       ├── Widgets
│       └── Theme
│
├── main.py
├── make_icon.py
├── build_exe.bat
├── requirements.txt
├── LICENSE
└── README.md
```

## 🔒 Data & Privacy

KODIGO stores QR code history locally using SQLite.

On Windows, the database is stored at:

```text
%APPDATA%\KODIGO\history.db
```

No account or hosted service is required to generate QR codes.

## 🤝 Contributions

Contributions are welcome!

If you have ideas for new features, improvements, or bug fixes, feel free to contribute. You can help improve KODIGO by:

- Reporting bugs or unexpected behavior through GitHub Issues.
- Suggesting new features and enhancements.
- Submitting pull requests with improvements or fixes.
- Improving documentation and overall usability.

Please ensure that your changes are tested and clearly explained before submitting a pull request.

Every contribution, whether big or small, is appreciated!

## 👨‍💻 Author

**Joshua C. Arao - 1st year ComSci student**

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for more information.

---

<p align="center">
  **KODIGO — Create. Customize. Connect.**
  <br/>
  Made with Python.
</p>
