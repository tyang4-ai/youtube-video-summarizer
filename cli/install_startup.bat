@echo off
echo Creating startup shortcut for YT Summarizer...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([Environment]::GetFolderPath('Startup') + '\YT Summarizer.lnk'); $s.TargetPath = '%~dp0run.bat'; $s.WorkingDirectory = '%~dp0'; $s.WindowStyle = 7; $s.Save()"
echo.
echo Done! YT Summarizer will run automatically when you start your computer.
echo Location: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\YT Summarizer.lnk
echo.
echo To remove, run uninstall_startup.bat
pause
