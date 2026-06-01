import asyncio
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from audiotranscriber.api.security import ApiKeyMiddleware
from audiotranscriber.config import get_app_config
from audiotranscriber.core.settings import TranscriptionSettings
from audiotranscriber.services import TranscriptionService

app = FastAPI(title="AudioTranscriber")
app.add_middleware(ApiKeyMiddleware)
_executor = ThreadPoolExecutor(max_workers=1)
_service = TranscriptionService()


@app.get("/health")
async def health():
    cfg = get_app_config()
    whisper = TranscriptionSettings.from_env()
    return {
        "status": "ok",
        "model": whisper.model_size,
        "device": _service.device,
        "bind": f"{cfg.api_host}:{cfg.api_port}",
        "auth_required": bool(cfg.api_key),
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    timestamps: bool = Query(False, description="Incluir [início - fim] em cada linha"),
    quality: str = Query(
        "equilibrada",
        description="Preset: rapida | equilibrada | alta",
    ),
    model: str | None = Query(None, description="Sobrescreve o modelo do preset"),
    language: str = Query("pt", description="Código do idioma ou auto"),
    export_format: str = Query("txt", description="txt | srt | vtt | json"),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo ausente.")

    if quality not in ("rapida", "equilibrada", "alta"):
        raise HTTPException(status_code=400, detail="quality inválido.")

    if export_format not in ("txt", "srt", "vtt", "json"):
        raise HTTPException(status_code=400, detail="export_format inválido.")

    settings = TranscriptionSettings.from_quality_preset(quality)
    if model:
        settings.model_size = model
    settings.language = language

    suffix = os.path.splitext(file.filename)[1] or ".bin"
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(
            _executor,
            lambda: _service.transcribe_path(
                tmp_path,
                settings=settings,
                include_timestamps=timestamps,
                export_format=export_format,
            ),
        )

        return {"text": text, "format": export_format}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def run() -> None:
    import uvicorn

    cfg = get_app_config()
    uvicorn.run(app, host=cfg.api_host, port=cfg.api_port)
