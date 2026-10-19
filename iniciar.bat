@echo off
setlocal
title Expenses - inicializacao
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
if errorlevel 1 (
    echo.
    echo A inicializacao encontrou um problema. Veja a mensagem acima.
    pause
)
