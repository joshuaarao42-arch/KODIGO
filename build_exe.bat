@echo off
REM Builds KODIGO.exe (windowed, no console) with PyInstaller.
python -m pip install -r requirements.txt pyinstaller
python make_icon.py
pyinstaller --noconfirm --clean --windowed --name KODIGO ^
  --icon assets\kodigo.ico ^
  --collect-all customtkinter ^
  --collect-submodules qrcode ^
  main.py
echo.
echo Done. Find the app in dist\KODIGO\KODIGO.exe
pause
