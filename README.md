# AudioTranscriber

API em FastAPI para transcrever áudios e vídeos em texto, usando [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Requisitos

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) no PATH (necessário para mp3, mp4, mkv e outros formatos)

## Instalação

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Executar

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Documentação interativa: http://127.0.0.1:8000/docs

## Uso

```bash
curl -X POST "http://127.0.0.1:8000/transcribe" -F "file=@audio.mp3"
```

Resposta:

```json
{"text": "texto transcrito..."}
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `WHISPER_MODEL` | `base` | Modelo (`tiny`, `base`, `small`, `medium`, `large-v3`, …) |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda` ou `auto` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` (GPU costuma usar `float16`) |
| `WHISPER_LANGUAGE` | `pt` | Código do idioma |

Exemplo com GPU:

```bash
set WHISPER_DEVICE=cuda
set WHISPER_COMPUTE_TYPE=float16
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoint

- `GET /health` — status da API
- `POST /transcribe` — envia um arquivo (`file`) de áudio ou vídeo
