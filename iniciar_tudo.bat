@echo off
title EINSTEIN AI HUBS - INICIALIZADOR COMPLETO
color 0B

echo ======================================================================
echo          INICIALIZANDO SISTEMA EINSTEIN AI ROULETTE HUD
echo ======================================================================
echo.

:: 1. Iniciar Ollama se nao estiver rodando
echo [1/3] Verificando Ollama local...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo    - Ollama ja esta em execucao.
) else (
    echo    - Iniciando servidor do Ollama em segundo plano...
    start "Ollama Server" /MIN ollama serve
    timeout /t 3 /nobreak >nul
)

:: 2. Iniciar Servidor Ponte (Bridge Node.js)
echo [2/3] Verificando Servidor Ponte Node.js (Porta 4000)...
netstat -ano | findstr :4000 >nul
if "%ERRORLEVEL%"=="0" (
    echo    - Servidor Ponte ja esta rodando na porta 4000.
) else (
    echo    - Iniciando Servidor Ponte Node.js...
    cd /d "c:\Users\Victor Ads\Desktop\ROLETA\oc-digodaroleta-main\bridge"
    start "Einstein HUD Bridge" cmd /k "node server.js"
    cd /d "c:\Users\Victor Ads\Desktop\ROLETA\oc-digodaroleta-main"
    timeout /t 2 /nobreak >nul
)

:: 3. Selecionar o Script da Roleta
echo.
echo ======================================================================
echo  [3/3] SELECIONE A ROLETA PARA INICIAR:
echo ======================================================================
echo   [1] Roleta Visual (main.py - Captura por Tela/Playwright)
echo   [2] Roleta Playtech (main_playtech.py - Captura por WebSocket)
echo ======================================================================
set /p opcao="Digite a opcao desejada (1 ou 2) e pressione Enter: "

if "%opcao%"=="2" goto playtech

:visual
echo    - Iniciando Roleta Visual padrao (main.py)...
start "Einstein Bot IA - Visual" cmd /k ".venv\Scripts\python.exe main.py"
goto end_start

:playtech
echo    - Iniciando Roleta Playtech (main_playtech.py)...
start "Einstein Bot IA - Playtech" cmd /k ".venv\Scripts\python.exe main_playtech.py"

:end_start

echo.
echo ======================================================================
echo  SISTEMA EINSTEIN INICIADO COM SUCESSO!
echo ======================================================================
echo  - Ollama esta rodando em segundo plano.
echo  - Servidor da Ponte esta rodando em uma janela separada.
echo  - O bot da roleta selecionado foi iniciado.
echo  - Agora basta abrir/atualizar o seu cassino no Chrome e jogar!
echo ======================================================================
echo.
pause
