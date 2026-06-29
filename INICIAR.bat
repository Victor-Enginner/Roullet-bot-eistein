@echo off
REM ====================================================================
REM  EINSTEIN ROULETTE AI HUD - clique duplo para iniciar tudo
REM  Chama o iniciar.ps1 (Ollama + Ponte + Bot) com bypass de policy.
REM ====================================================================
title Einstein Roulette AI HUD
cd /d "%~dp0"
pwsh -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1"
echo.
echo (O bot encerrou. Pode fechar esta janela.)
pause
