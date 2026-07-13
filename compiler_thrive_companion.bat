@echo off
setlocal EnableDelayedExpansion

echo [compiler] Building THRIVE companion with Nuitka...
call .venv\Scripts\activate.bat

set NUITKA_OPTS=
if defined CI set NUITKA_OPTS=--assume-yes-for-downloads

python -m nuitka --standalone --follow-imports !NUITKA_OPTS! ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --windows-console-mode=disable ^
    --output-filename=WIIBBLE-THRIVE.exe ^
    --output-dir=dist_nuitka_thrive ^
    --include-package=paho ^
    --nofollow-import-to=dearpygui ^
    --nofollow-import-to=hid ^
    --nofollow-import-to=pythonnet ^
    --nofollow-import-to=wiibble.ui ^
    --nofollow-import-to=wiibble.session ^
    --nofollow-import-to=wiibble.__main__ ^
    --nofollow-import-to=wiibble.cli.report ^
    --nofollow-import-to=wiibble.session_report ^
    src\wiibble\thrive\__main__.py
if errorlevel 1 (
    echo [compiler] THRIVE COMPANION BUILD FAILED.
    exit /b 1
)

set MAIN_DIST=dist_nuitka\wiibble.dist
set COMPANION_DIST=dist_nuitka_thrive\thrive.dist

if not exist "%MAIN_DIST%" (
    echo [compiler] Main dist not found at %MAIN_DIST% — build WIIBBLE.exe first.
    exit /b 1
)

set COMPANION_INSTALL=%MAIN_DIST%\thrive
if exist "%COMPANION_INSTALL%" rmdir /s /q "%COMPANION_INSTALL%"

echo [compiler] Installing THRIVE companion into %COMPANION_INSTALL%...
mkdir "%COMPANION_INSTALL%"
xcopy /E /Y /I "%COMPANION_DIST%\*" "%COMPANION_INSTALL%\"
if errorlevel 1 (
    echo [compiler] FAILED to install THRIVE companion dist.
    exit /b 1
)

echo [compiler] THRIVE companion ready: %COMPANION_INSTALL%\WIIBBLE-THRIVE.exe
