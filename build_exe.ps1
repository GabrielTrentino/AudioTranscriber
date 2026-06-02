# Gera executável Windows da interface gráfica (gui.py).
# Requer: venv com requirements.txt + [diarization] + scripts/requirements-build.txt

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Error "Crie o venv antes: python -m venv .venv; pip install -r requirements.txt -r scripts/requirements-build.txt; pip install -e `".[diarization]`""
}

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
    --collect-all pyannote.audio `
    --collect-all torch `
    --collect-all torchaudio `
    --collect-submodules pyannote `
    --hidden-import av `
    --hidden-import huggingface_hub `
    --hidden-import tokenizers `
    --hidden-import safetensors `
    --hidden-import einops `
    --hidden-import lightning `
    --hidden-import pyannote.audio `
    --hidden-import pyannote.core `
    --hidden-import pyannote.database `
    --hidden-import pyannote.metrics `
    --hidden-import pyannote.pipeline `
    --hidden-import audiotranscriber `
    --hidden-import audiotranscriber.gui.app `
    --hidden-import audiotranscriber.core.ffmpeg `
    --hidden-import audiotranscriber.core.startup_checks `
    --hidden-import audiotranscriber.services.diarization_backend `
    --hidden-import audiotranscriber.services.diarization_pyannote `
    --hidden-import audiotranscriber.services.diarization_common `
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

# FFmpeg ao lado do .exe (transcrição e diarização)
$ffmpegSrc = $null
if (Test-Path (Join-Path $dist "ffmpeg.exe")) {
    $ffmpegSrc = "ja presente"
} else {
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) {
        Copy-Item $cmd.Source $dist -Force
        $ffmpegSrc = $cmd.Source
    }
}

# secrets/ ao lado do .exe (HF_TOKEN para diarização)
$secretsDist = Join-Path $dist "secrets"
New-Item -ItemType Directory -Force -Path $secretsDist | Out-Null
$example = Join-Path $PSScriptRoot "secrets\.env.example"
if (Test-Path $example) {
    Copy-Item $example (Join-Path $secretsDist ".env.example") -Force
}
$envLocal = Join-Path $PSScriptRoot "secrets\.env"
if (Test-Path $envLocal) {
    Copy-Item $envLocal (Join-Path $secretsDist ".env") -Force
    Write-Host "secrets\.env copiado para dist (uso local)."
} else {
    Write-Host "AVISO: secrets\.env nao encontrado na raiz do projeto."
    Write-Host "        Copie secrets\.env.example para dist\AudioTranscriber\secrets\.env e defina HF_TOKEN."
}

Write-Host ""
Write-Host "Pronto: $exe"
Write-Host "Python empacotado: $($pythonDll.Name)"
if ($ffmpegSrc -and $ffmpegSrc -ne "ja presente") {
    Write-Host "FFmpeg copiado de: $ffmpegSrc"
}
Write-Host ""
Write-Host "IMPORTANTE: use SOMENTE a pasta dist\AudioTranscriber\ (nao execute nada em build\)."
Write-Host "Diarizacao: marque 'Identificar falantes' na GUI; HF_TOKEN em dist\AudioTranscriber\secrets\.env"
Write-Host "Na primeira execucao: download Whisper + modelo pyannote (internet + termos HF aceitos)."
Write-Host "Se ainda falhar, instale: https://aka.ms/vs/17/release/vc_redist.x64.exe"
