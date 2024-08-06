if not exist outputBuild\ mkdir outputBuild\
@REM if not exist outputBuild\WiiBalanceBoardConnection\ mkdir outputBuild\WiiBalanceBoardConnection\
call venv\Scripts\activate.bat
pyinstaller --clean --onefile --noconsole scale.py --icon=images\\logo.ico --name=WIIBBLE --hidden-import=hid --add-data="images;images" --add-data="WiiBalanceBoardConnection;WiiBalanceBoardConnection"
move dist\\WIIBBLE.exe outputBuild\\WIIBBLE.exe
rmdir /s /q build
del /f /q WIIBBLE.spec
rmdir /s /q dist
@REM @REM build c# project and move content of \bin\Debug\net8.0
@REM cd WiiBalanceBoardConnection
@REM dotnet build
@REM cd bin\Debug\net8.0
@REM @REM create the outputBuild folder if it does not exist
@REM copy *.* ..\..\..\..\outputBuild\WiiBalanceBoardConnection\
@REM cd ..\..\..\..
@REM @REM copy the images folder and its content to the outputBuild folder
@REM @REM xcopy images outputBuild\images\ /E /Y