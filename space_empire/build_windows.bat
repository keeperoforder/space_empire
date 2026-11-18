@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean SpaceEmpire.spec
echo.
echo Build finished. Output: dist\SpaceEmpire\SpaceEmpire.exe
pause
