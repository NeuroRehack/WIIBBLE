@REM build c# project and move content of \bin\Debug\net8.0
cd WiiBalanceBoardLibrary
dotnet build
cd ..
if not exist outputBuild\ mkdir outputBuild\
call venv\Scripts\activate.bat
pyinstaller --clean --onefile --noconsole main.py --icon=images\\logo.ico --name=WIIBBLE --hidden-import=hid --add-data="images;images" --add-data="WiiBalanceBoardLibrary;WiiBalanceBoardLibrary"
move dist\\WIIBBLE.exe outputBuild\\WIIBBLE.exe
rmdir /s /q build
del /f /q WIIBBLE.spec
rmdir /s /q dist
