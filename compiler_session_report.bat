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

echo [compiler] Merging session-report companion into %MAIN_DIST%...
xcopy /E /Y /I "%COMPANION_DIST%\*" "%MAIN_DIST%\"
if errorlevel 1 (
    echo [compiler] FAILED to merge companion dist into main dist.
    exit /b 1
)

echo [compiler] Session report companion ready: %MAIN_DIST%\WIIBBLE-SessionReport.exe
