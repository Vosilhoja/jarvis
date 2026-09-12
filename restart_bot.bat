@echo off  
taskkill /F /IM pythonw.exe /T  
timeout /t 2 /nobreak >nul  
start ^ ^ ^ ^ C:\Users\vosil\AppData\Local\Programs\Python\Python312\pythonw.exe watchdog.py 
