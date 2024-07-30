call venv\Scripts\activate.bat
pyinstaller --onefile --noconsole scale.py  --icon=images\\logo.ico --name=WIIBBLE --hidden-import=hid 
move dist\\WIIBBLE.exe WIIBBLE.exe
@REM delete directory build
rmdir /s /q build
del /f /q WIIBBLE.spec
rmdir /s /q dist