@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Konstruas Redaktilo.exe (Windows).
REM Necesas Python 3 kun tkinter (la instalilo de python.org inkluzivas gxin).
REM Rezulto: dosierujo dist\Redaktilo kun Redaktilo.exe kaj la kromprogramoj.

where py >nul 2>&1
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% -m pip install --upgrade pyinstaller spylls
if errorlevel 1 goto eraro

REM La normaj moduloj en moduloj.txt estas enpakitaj en la .exe, por ke la kromprogramoj povu uzi ilin.
set HID=--hidden-import htmlumilo --hidden-import monato_common
for /f "usebackq delims=" %%M in ("moduloj.txt") do set HID=!HID! --hidden-import %%M

%PY% -m PyInstaller --noconfirm --clean --windowed --name Redaktilo --collect-submodules spylls !HID! editor.py
if errorlevel 1 goto eraro

REM La kromprogramoj estas apud la .exe (ne enpakitaj): oni povas aldoni novajn.
xcopy /E /I /Y kromprogramoj "dist\Redaktilo\kromprogramoj" >nul
copy /Y LEGUMIN.txt "dist\Redaktilo\" >nul
copy /Y LICENCO.txt "dist\Redaktilo\" >nul
xcopy /E /I /Y vortaroj "dist\Redaktilo\vortaroj" >nul
xcopy /E /I /Y lingvoj "dist\Redaktilo\lingvoj" >nul
xcopy /E /I /Y licencoj "dist\Redaktilo\licencoj" >nul

if not exist "dist\Redaktilo\Redaktilo.exe" goto eraro
REM Forigi la provizorajn dosierojn (la dosierujo "build" NE enhavas la finan programon).
if exist build rmdir /s /q build
if exist Redaktilo.spec del /q Redaktilo.spec
echo.
echo FINITE. Uzu nur la programon en: %CD%\dist\Redaktilo\Redaktilo.exe
echo (Konservu la tutan dosierujon dist\Redaktilo, ne nur la .exe.)
pause
exit /b 0

:eraro
echo.
echo ERARO dum la konstruo.
pause
exit /b 1
