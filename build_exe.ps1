# Gera executável Windows da interface gráfica (gui.py).
# Requer: venv ativo com requirements.txt + requirements-build.txt instalados.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Crie o venv antes: python -m venv .venv; pip install -r requirements.txt -r requirements-build.txt"
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name AudioTranscriber `
    --onedir `
    --collect-all faster_whisper `
    --collect-all ctranslate2 `
    --collect-all onnxruntime `
    --hidden-import av `
    --hidden-import huggingface_hub `
    --hidden-import tokenizers `
    gui.py

Write-Host ""
Write-Host "Pronto: dist\AudioTranscriber\AudioTranscriber.exe"
Write-Host "Opcional: copie ffmpeg.exe para dist\AudioTranscriber\"
Write-Host "Na primeira execucao o modelo Whisper sera baixado (precisa de internet uma vez)."
