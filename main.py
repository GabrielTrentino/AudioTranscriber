import asyncio
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, UploadFile

from transcriber import DEVICE, MODEL_SIZE, transcribe_path

app = FastAPI(title="AudioTranscriber")
executor = ThreadPoolExecutor(max_workers=1)


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_SIZE, "device": DEVICE}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome do arquivo ausente.")

    suffix = os.path.splitext(file.filename)[1] or ".bin"
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        text = await asyncio.get_running_loop().run_in_executor(
            executor, transcribe_path, tmp_path
        )

        return {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
