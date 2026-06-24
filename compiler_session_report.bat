@echo off
setlocal EnableDelayedExpansion

echo [compiler] Building session-report companion with Nuitka...
call .venv\Scripts\activate.bat

set NUITKA_OPTS=
if defined CI set NUITKA_OPTS=--assume-yes-for-downloads

python -m nuitka --standalone --follow-imports !NUITKA_OPTS! ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --windows-console-mode=disable ^
    --output-filename=WIIBBLE-SessionReport.exe ^
    --output-dir=dist_nuitka_session_report ^
    --include-package=plotly ^
    --include-package-data=plotly ^
    --nofollow-import-to=dearpygui ^
    --nofollow-import-to=hid ^
    --nofollow-import-to=pythonnet ^
    --nofollow-import-to=wiibble.ui ^
    --nofollow-import-to=wiibble.session ^
    --nofollow-import-to=wiibble.__main__ ^
    src\wiibble\cli\session_report.py
if errorlevel 1 (
    echo [compiler] SESSION REPORT BUILD FAILED.
    exit /b 1
)

set MAIN_DIST=dist_nuitka\wiibble.dist
set COMPANION_DIST=dist_nuitka_session_report\session_report.dist

if not exist "%MAIN_DIST%" (
    echo [compiler] Main dist not found at %MAIN_DIST% — build WIIBBLE.exe first.
    exit /b 1
)

set COMPANION_INSTALL=%MAIN_DIST%\session_report
if exist "%COMPANION_INSTALL%" rmdir /s /q "%COMPANION_INSTALL%"

echo [compiler] Installing session-report companion into %COMPANION_INSTALL%...
@REM Keep companion DLLs separate from the main app — merging both Nuitka
@REM standalone dists into one folder overwrites shared runtime files and
@REM breaks WIIBBLE.exe at startup.
mkdir "%COMPANION_INSTALL%"
xcopy /E /Y /I "%COMPANION_DIST%\*" "%COMPANION_INSTALL%\"
if errorlevel 1 (
    echo [compiler] FAILED to install companion dist.
    exit /b 1
)

echo [compiler] Session report companion ready: %COMPANION_INSTALL%\WIIBBLE-SessionReport.exe
