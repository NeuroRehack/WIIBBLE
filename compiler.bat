@echo off

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

echo [compiler] Building with Nuitka (standalone)...
python -m nuitka --standalone --follow-imports ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --windows-icon-from-ico=images\logo.ico ^
    --output-filename=WIIBBLE.exe ^
    --output-dir=dist_nuitka ^
    --windows-console-mode=disable ^
    --include-package=dearpygui ^
    --include-package=hid ^
    --include-package=numpy ^
    --include-package=pygments ^
    --include-module=tkinter ^
    --nofollow-import-to=analysis ^
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
    main.py
if errorlevel 1 (
    echo [compiler] BUILD FAILED.
    exit /b 1
)
@REM if exist outputBuild\WIIBBLE rmdir /s /q outputBuild\WIIBBLE
@REM move dist_nuitka\main.dist outputBuild\WIIBBLE
echo [compiler] Build complete. Output: dist_nuitka\main.dist\WIIBBLE.exe

echo.
where iscc >nul 2>&1
if errorlevel 1 (
    echo [installer] Inno Setup ^(iscc^) not found on PATH — skipping installer build.
    echo [installer] Install Inno Setup 6.x from https://jrsoftware.org/isinfo.php to enable.
) else (
    echo [installer] Building installer with Inno Setup...
    if not exist installer_output\ mkdir installer_output\
    iscc installer.iss
    if errorlevel 1 (
        echo [installer] INSTALLER BUILD FAILED.
        exit /b 1
    )
    echo [installer] Installer ready: installer_output\WIIBBLE-0.1.0-Setup.exe
)