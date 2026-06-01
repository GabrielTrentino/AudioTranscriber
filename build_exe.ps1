# Gera executável Windows da interface gráfica (gui.py).
# Requer: venv ativo com requirements.txt + requirements-build.txt instalados.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Crie o venv antes: python -m venv .venv; pip install -r requirements.txt -r requirements-build.txt"
}

# UPX desligado: evita falha ao carregar python3xx.dll no Windows
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --noupx `
    --windowed `
    --name AudioTranscriber `
    --onedir `
    --paths src `
    --collect-all faster_whisper `
    --collect-all ctranslate2 `
    --collect-all onnxruntime `
    --hidden-import av `
    --hidden-import huggingface_hub `
    --hidden-import tokenizers `
    --hidden-import audiotranscriber `
    --hidden-import audiotranscriber.gui.app `
    --hidden-import audiotranscriber.core.ffmpeg `
    --hidden-import audiotranscriber.core.startup_checks `
    gui.py

$dist = Join-Path $PSScriptRoot "dist\AudioTranscriber"
$exe = Join-Path $dist "AudioTranscriber.exe"
$pythonDll = Get-ChildItem (Join-Path $dist "_internal") -Filter "python3*.dll" -ErrorAction SilentlyContinue

if (-not (Test-Path $exe)) {
    Write-Error "Build falhou: $exe nao foi criado."
}
if (-not $pythonDll) {
    Write-Error "Build incompleto: python3*.dll nao encontrado em dist\AudioTranscriber\_internal"
}

Write-Host ""
Write-Host "Pronto: $exe"
Write-Host "Python empacotado: $($pythonDll.Name)"
Write-Host ""
Write-Host "IMPORTANTE: use SOMENTE a pasta dist\AudioTranscriber\ (nao execute nada em build\)."
Write-Host "Opcional: copie ffmpeg.exe para dist\AudioTranscriber\"
Write-Host "Se ainda falhar, instale: https://aka.ms/vs/17/release/vc_redist.x64.exe"
Write-Host "Na primeira execucao o modelo Whisper sera baixado (precisa de internet uma vez)."
