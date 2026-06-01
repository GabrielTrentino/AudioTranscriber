# Layout do repositório

## Por que existe `AudioTranscriber/AudioTranscriber/`?

Ao clonar `https://github.com/GabrielTrentino/AudioTranscriber`, o Git cria:

```text
AudioTranscriber/          ← pasta do clone (nome do repositório)
  AudioTranscriber/        ← raiz real do código (README, gui.py, src/)
```

Isso é comum quando o repositório remoto já se chama `AudioTranscriber`. **Trabalhe sempre dentro da pasta interna** (onde estão `gui.py`, `src/` e `README.md`).

## Estrutura atual (após P0)

```text
AudioTranscriber/              ← raiz do projeto (use esta pasta)
  src/
    audiotranscriber/
      config/                  AppConfig (env + config.yaml)
      core/                    settings, model manager, formatter
      services/                TranscriptionService
      api/                     FastAPI
      gui/
        views/                 widgets tkinter
        controller.py          jobs sem Whisper na UI
        app.py                 janela principal
  gui.py                       atalho: python gui.py
  main.py                      atalho: uvicorn
  transcriber.py               compatibilidade imports antigos
  config.yaml.example
  docs/
  build_exe.ps1
  dist/                        executável (gerado)
```

## Como executar

```powershell
cd AudioTranscriber\AudioTranscriber   # pasta interna após clone
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
python gui.py
```

Ou sem instalar o pacote:

```powershell
pip install -r requirements.txt
python gui.py
```

(`_path_setup.py` adiciona `src/` ao `PYTHONPATH` automaticamente.)

## Executável

O `.exe` fica em `dist\AudioTranscriber\`. O log `last_run.log` é criado **na mesma pasta do executável**.
