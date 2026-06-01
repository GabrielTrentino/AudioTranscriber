# Arquitetura — AudioTranscriber

Visão geral do pacote `src/audiotranscriber/` após a refatoração P0/P2.

## Camadas

```mermaid
flowchart TB
    subgraph entry [Pontos de entrada]
        GUI[gui.py / TranscriberApp]
        CLI[python -m audiotranscriber]
        API[audiotranscriber-api / FastAPI]
    end

    subgraph app_layer [Aplicação]
        CTRL[gui.controller]
        CLIM[cli.py]
        APIAPP[api.app]
    end

    subgraph services [Serviços]
        TS[TranscriptionService]
        JQ[JobQueue]
        DIA[diarization opcional]
    end

    subgraph core [Núcleo]
        MM[ModelManager]
        FMT[formatter / exporters]
        CFG[AppConfig]
    end

    subgraph external [Externo]
        FW[faster-whisper]
        FF[FFmpeg]
    end

    GUI --> CTRL
    CLI --> CLIM
    API --> APIAPP
    CTRL --> TS
    CLIM --> TS
    CLIM --> JQ
    APIAPP --> TS
    TS --> MM
    TS --> FMT
    TS --> DIA
    MM --> FW
    TS --> FF
    MM --> CFG
    FMT --> CFG
```

## Fluxo de transcrição (GUI)

```mermaid
sequenceDiagram
    participant U as Usuário
    participant UI as TranscriberApp
    participant Q as UI Queue
    participant C as Controller
    participant S as TranscriptionService
    participant M as ModelManager

    U->>UI: Transcrever
    UI->>UI: Worker thread
    UI->>C: run_single / run_batch
    C->>S: transcribe_to_file
    S->>M: get_model
    M-->>S: WhisperModel
    S->>S: transcribe + format
    S-->>C: output Path
    C-->>UI: callback via queue
    UI->>Q: progress / done
    Q->>UI: after() na thread principal
```

## ModelManager

- Cache de modelos por chave `(model_size, compute_type, device)`.
- `threading.Lock` para requisições concorrentes na API.
- Uma instância global via `get_model_manager()` (substitui singleton ad hoc).

## Configuração

| Fonte | Prioridade |
|-------|------------|
| Variáveis `WHISPER_*` | Mais alta |
| `config.yaml` na raiz do projeto | Média |
| Defaults em `AppConfig` | Mais baixa |

## Módulos

| Pacote | Responsabilidade |
|--------|------------------|
| `config/` | `AppConfig`, host API, CORS, rate limit |
| `core/` | Settings, formatter, exporters, FFmpeg, startup |
| `services/` | Transcrição, fila, diarização |
| `gui/` | Views tkinter, controller, app |
| `api/` | FastAPI, auth opcional |
| `cli.py` | `transcribe`, `batch`, `queue` |

## Deploy

| Modo | Artefato |
|------|----------|
| Desktop | `dist/AudioTranscriber/` (PyInstaller) |
| API local | `audiotranscriber-api` → `127.0.0.1:8000` |
| API Docker | `Dockerfile` → imagem headless |

Ver também: [PROJECT_LAYOUT.md](PROJECT_LAYOUT.md).
