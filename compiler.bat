if not exist outputBuild\ mkdir outputBuild\
if not exist outputBuild\WiiBalanceBoardConnection\ mkdir outputBuild\WiiBalanceBoardConnection\
call venv\Scripts\activate.bat
pyinstaller --clean --onefile --noconsole scale.py  --icon=images\\logo.ico --name=WIIBBLE --hidden-import=hid 
move dist\\WIIBBLE.exe outputBuild\\WIIBBLE.exe
rmdir /s /q build
del /f /q WIIBBLE.spec
rmdir /s /q dist
@REM build c# project and move content of \bin\Debug\net8.0
cd WiiBalanceBoardConnection
dotnet build
cd bin\Debug\net8.0
@REM create the outputBuild folder if it does not exist
move *.* ..\..\..\..\outputBuild\WiiBalanceBoardConnection\
cd ..\..\..\..
@REM copy the images folder and its content to the outputBuild folder
xcopy images outputBuild\images\ /E /Y