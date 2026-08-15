@echo off
setlocal EnableDelayedExpansion

if not defined WIIBBLE_VERSION (
    for /f "delims=" %%V in ('python scripts\get_version.py') do set WIIBBLE_VERSION=%%V
)
if not defined WIIBBLE_PROFILE set WIIBBLE_PROFILE=full
echo [compiler] Version: %WIIBBLE_VERSION%
echo [compiler] Profile: %WIIBBLE_PROFILE%

echo [compiler] Building C# library...
cd WiiBalanceBoardLibrary
dotnet build
if errorlevel 1 (
    echo [compiler] C# BUILD FAILED.
    exit /b 1
)
cd ..

@REM if not exist outputBuild\ mkdir outputBuild\
call .venv\Scripts\activate.bat

set FEATURE_THRIVE=1
set FEATURE_SESSION_REPORT=1
set APP_FLAVOR=
python scripts\write_product_overlay.py > "%TEMP%\wiibble_product_flags.txt"
if errorlevel 1 (
    echo [compiler] PRODUCT OVERLAY FAILED.
    python scripts\write_product_overlay.py --clean
    exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%A in ("%TEMP%\wiibble_product_flags.txt") do (
    if /I "%%A"=="THRIVE" set FEATURE_THRIVE=%%B
    if /I "%%A"=="SESSION_REPORT" set FEATURE_SESSION_REPORT=%%B
    if /I "%%A"=="APP_FLAVOR" set APP_FLAVOR=%%B
)
@REM The full build emits the "none" sentinel because an empty value cannot be parsed.
if /I "!APP_FLAVOR!"=="none" set APP_FLAVOR=
echo [compiler] Features: thrive=!FEATURE_THRIVE! session_report=!FEATURE_SESSION_REPORT!

echo [compiler] Building with Nuitka (standalone)...
set NUITKA_OPTS=
if defined CI set NUITKA_OPTS=--assume-yes-for-downloads
set NUITKA_EXTRA=
if "!FEATURE_SESSION_REPORT!"=="0" set NUITKA_EXTRA=--nofollow-import-to=wiibble.session_report
python -m nuitka --standalone --follow-imports !NUITKA_OPTS! !NUITKA_EXTRA! ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --windows-icon-from-ico=images\logoPerson.ico ^
    --output-filename=WIIBBLE.exe ^
    --output-dir=dist_nuitka ^
    --windows-console-mode=disable ^
    --include-package=dearpygui ^
    --include-package=hid ^
    --include-package=numpy ^
    --include-package=pygments ^
    --include-module=tkinter ^
    --nofollow-import-to=wiibble.analysis.analysis ^
    --nofollow-import-to=wiibble.cli.report ^
    --nofollow-import-to=wiibble.cli.process_recordings ^
    --nofollow-import-to=wiibble.cli.session_report ^
    --nofollow-import-to=wiibble.session_report.runner ^
    --nofollow-import-to=wiibble.thrive ^
    --nofollow-import-to=code_descriptors_postural_control ^
    --nofollow-import-to=scipy ^
    --nofollow-import-to=pandas ^
    --nofollow-import-to=sklearn ^
    --nofollow-import-to=statsmodels ^
    --nofollow-import-to=joblib ^
    --nofollow-import-to=patsy ^
    --include-data-dir=images=images ^
    --include-data-dir=assets\fonts=assets\fonts ^
    --include-data-files=WiiBalanceBoardLibrary\bin\Debug\net48\*.dll=WiiBalanceBoardLibrary\bin\Debug\net48\ ^
    --include-data-files=WiiBalanceBoardLibrary\bin\Debug\net48\*.pdb=WiiBalanceBoardLibrary\bin\Debug\net48\ ^
    src\wiibble
set BUILD_ERR=!errorlevel!
python scripts\write_product_overlay.py --clean
if !BUILD_ERR! neq 0 (
    echo [compiler] BUILD FAILED.
    exit /b 1
)
@REM if exist outputBuild\WIIBBLE rmdir /s /q outputBuild\WIIBBLE
@REM move dist_nuitka\main.dist outputBuild\WIIBBLE
echo [compiler] Build complete. Output: dist_nuitka\wiibble.dist\WIIBBLE.exe

@REM Nuitka reuses dist_nuitka\wiibble.dist, so a previous full build would otherwise
@REM leave its companion folders behind and ship them in a lite build.
if "!FEATURE_SESSION_REPORT!"=="0" (
    echo [compiler] Skipping session-report companion ^(FEATURE_SESSION_REPORT=0^).
    if exist dist_nuitka\wiibble.dist\session_report rmdir /s /q dist_nuitka\wiibble.dist\session_report
) else (
    call compiler_session_report.bat
    if errorlevel 1 (
        echo [compiler] SESSION REPORT COMPANION BUILD FAILED.
        exit /b 1
    )
)

if "!FEATURE_THRIVE!"=="0" (
    echo [compiler] Skipping THRIVE companion ^(FEATURE_THRIVE=0^).
    if exist dist_nuitka\wiibble.dist\thrive rmdir /s /q dist_nuitka\wiibble.dist\thrive
) else (
    call compiler_thrive_companion.bat
    if errorlevel 1 (
        echo [compiler] THRIVE COMPANION BUILD FAILED.
        exit /b 1
    )
)

echo.
where iscc >nul 2>&1
if errorlevel 1 (
    echo [installer] Inno Setup ^(iscc^) not found on PATH — skipping installer build.
    echo [installer] Install Inno Setup 6.x from https://jrsoftware.org/isinfo.php to enable.
) else (
    echo [installer] Building installer with Inno Setup...
    if not exist installer_output\ mkdir installer_output\
    @REM Assign the name first: a successful `set` clears errorlevel and would hide an iscc failure.
    if "!APP_FLAVOR!"=="" (
        set INSTALLER_NAME=WIIBBLE-%WIIBBLE_VERSION%-Setup.exe
        iscc /DAppVersion=%WIIBBLE_VERSION% installer.iss
    ) else (
        set INSTALLER_NAME=WIIBBLE-%WIIBBLE_VERSION%-!APP_FLAVOR!-Setup.exe
        iscc /DAppVersion=%WIIBBLE_VERSION% /DAppFlavor=!APP_FLAVOR! installer.iss
    )
    if errorlevel 1 (
        echo [installer] INSTALLER BUILD FAILED.
        exit /b 1
    )
    echo [installer] Installer ready: installer_output\!INSTALLER_NAME!
)
