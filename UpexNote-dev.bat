@echo off
title UpexNote (dev) - NAO FECHAR enquanto usas a app
echo.
echo   A iniciar o UpexNote... a janela da app abre daqui a uns segundos.
echo   MANTEM esta janela aberta enquanto usas o UpexNote.
echo   Para fechar a app, fecha esta janela.
echo.
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
cd /d "%~dp0apps\desktop"
call npm run tauri dev
echo.
echo   (o UpexNote terminou - podes fechar esta janela)
pause
