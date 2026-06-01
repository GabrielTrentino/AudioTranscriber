import asyncio
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from audiotranscriber.core.settings import TranscriptionSettings
from audiotranscriber.services import TranscriptionService

app = FastAPI(title="AudioTranscriber")
_executor = ThreadPoolExecutor(max_workers=1)
_service = TranscriptionService()


@app.get("/health")
async def health():
    cfg = TranscriptionSettings.from_env()
    return {"status": "ok", "model": cfg.model_size, "device": _service.device}


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
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo ausente.")

    if quality not in ("rapida", "equilibrada", "alta"):
        raise HTTPException(status_code=400, detail="quality inválido.")

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
            ),
        )

        return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
