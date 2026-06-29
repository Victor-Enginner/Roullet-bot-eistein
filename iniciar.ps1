# ==========================================================================
#  EINSTEIN ROULETTE AI HUD  —  inicializador completo
#  Sobe automaticamente:  Ollama (IA)  +  Ponte (Node :4000)  +  Bot (Python)
#  A extensao do HUD (Chrome) e carregada UMA VEZ no navegador (instrucoes no fim).
# ==========================================================================
$ErrorActionPreference = "SilentlyContinue"
$proj = "C:\Users\Victor Ads\Desktop\ROLETA\oc-digodaroleta-main"
Set-Location $proj

function Test-OllamaUp {
    # 127.0.0.1 (IPv4) — é onde o Ollama liga e onde o bot conecta. NÃO usar
    # 'localhost' (o Windows resolve pra IPv6 ::1 primeiro e a checagem falha).
    try { Invoke-WebRequest "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -UseBasicParsing | Out-Null; return $true }
    catch { return $false }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  EINSTEIN ROULETTE AI HUD  -  iniciando o sistema" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# ---- 1/3  OLLAMA (IA local) ----
Write-Host "`n[1/3] Ollama (IA local)..." -ForegroundColor Yellow
if (Test-OllamaUp) {
    Write-Host "  ja esta no ar." -ForegroundColor Green
} else {
    Write-Host "  iniciando servidor em segundo plano (pode levar ~20-30s nesta maquina)..."
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    $ok = $false
    for ($i = 0; $i -lt 80; $i++) { Start-Sleep -Milliseconds 500; if (Test-OllamaUp) { $ok = $true; break } }  # ate 40s
    if ($ok) { Write-Host "  no ar." -ForegroundColor Green }
    else { Write-Host "  ainda subindo em segundo plano -> vai estar pronto quando voce entrar na roleta (o bot faz o preload). Se nao, usa a logica classica." -ForegroundColor DarkYellow }
}
if (Test-OllamaUp) {
    $models = (ollama list 2>$null) -join "`n"
    if ($models -notmatch "qwen2\.5:1\.5b") {
        Write-Host "  baixando modelo qwen2.5:1.5b (so na 1a vez, ~1GB)..." -ForegroundColor Yellow
        ollama pull qwen2.5:1.5b
    }
}

# ---- 2/3  PONTE de dados (Node :4000) em janela separada ----
Write-Host "`n[2/3] Ponte de dados (Node :4000)..." -ForegroundColor Yellow
$bridgeCmd = "Set-Location '$proj\bridge'; Write-Host 'PONTE :4000  (NAO FECHE ESTA JANELA)' -ForegroundColor Cyan; node server.js"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", $bridgeCmd
Start-Sleep -Seconds 2
Write-Host "  ponte iniciada em nova janela (deixe aberta)." -ForegroundColor Green

# ---- 3/3  BOT principal (aqui mesmo, interativo) ----
Write-Host "`n[3/3] Bot principal (main.py)..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  LEMBRETE - extensao do HUD no Chrome (so na 1a vez):" -ForegroundColor Magenta
Write-Host "    chrome://extensions  ->  Modo desenvolvedor  ->  Carregar sem compactacao" -ForegroundColor Magenta
Write-Host "    -> selecione a pasta:  $proj\chrome-extension" -ForegroundColor Magenta
Write-Host ""
Write-Host "  O bot vai ABRIR O NAVEGADOR. Faca login, entre na Roleta Brasileira," -ForegroundColor White
Write-Host "  abra o historico estendido e pressione ENTER quando o bot pedir." -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor DarkGray

# Producao: a extracao protobuf AO VIVO nao precisa gravar o .jsonl.
# (Se um dia precisar recapturar p/ recalibrar, troque para "True".)
$env:CAPTURE_PTIELIVE_FRAMES = "False"

python main.py
