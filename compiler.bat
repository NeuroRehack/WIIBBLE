@echo off

echo [compiler] Building C# library...
cd WiiBalanceBoardLibrary
dotnet build
if errorlevel 1 (
    echo [compiler] C# BUILD FAILED.
    exit /b 1
)
cd ..

if not exist outputBuild\ mkdir outputBuild\
call .venv\Scripts\activate.bat

echo [compiler] Building with Nuitka (standalone)...
python -m nuitka --standalone --follow-imports ^
    --windows-icon-from-ico=images\logo.ico ^
    --output-filename=WIIBBLE.exe ^
    --output-dir=dist_nuitka ^
    --include-package=dearpygui ^
    --include-package=hid ^
    --include-data-dir=images=images ^
    --include-data-dir=assets\fonts=assets\fonts ^
    --include-data-files=WiiBalanceBoardLibrary\bin\Debug\net48\*.dll=WiiBalanceBoardLibrary\bin\Debug\net48\ ^
    --include-data-files=WiiBalanceBoardLibrary\bin\Debug\net48\*.pdb=WiiBalanceBoardLibrary\bin\Debug\net48\ ^
    main.py
if errorlevel 1 (
    echo [compiler] BUILD FAILED.
    exit /b 1
)
if exist outputBuild\WIIBBLE rmdir /s /q outputBuild\WIIBBLE
move dist_nuitka\main.dist outputBuild\WIIBBLE
echo [compiler] Build complete. Output: outputBuild\WIIBBLE