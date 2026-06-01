# Layout do repositório

## Por que existe `AudioTranscriber/AudioTranscriber/`?

Ao clonar `https://github.com/GabrielTrentino/AudioTranscriber`, o Git cria:

```text
AudioTranscriber/          ← pasta do clone (nome do repositório)
  AudioTranscriber/        ← raiz real do código
```

**Trabalhe sempre na pasta interna** (onde estão `gui.py`, `src/` e `README.md`).

## Raiz do projeto (arquivos principais)

```text
AudioTranscriber/
  README.md
  LICENSE
  pyproject.toml
  requirements.txt
  gui.py                 ← python gui.py / PyInstaller
  build_exe.ps1
  src/audiotranscriber/  ← código
  docs/
  config/
  docker/
  scripts/
```

## Pacote `src/audiotranscriber/`

```text
  config/       AppConfig (env + config.yaml na raiz)
  core/         settings, ModelManager, formatter, exporters
  services/     TranscriptionService, fila, diarização
  api/          FastAPI
  gui/          views, controller, app
  cli.py        python -m audiotranscriber
```

## Como executar

```powershell
cd AudioTranscriber\AudioTranscriber
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python gui.py
```

API: `audiotranscriber-api` · CLI: `python -m audiotranscriber transcribe …`

## Executável e log

- Build: `.\build_exe.ps1` → `dist\AudioTranscriber\`
- `last_run.log` na **pasta de saída** do `.txt` (não na pasta do `.exe`)
