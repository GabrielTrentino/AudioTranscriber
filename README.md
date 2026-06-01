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

### Interface gráfica (recomendado)

Usa **tkinter** (biblioteca padrão do Python). Escolha o arquivo de entrada, a pasta de saída e clique em **Transcrever**. O texto é salvo como `{nome-do-arquivo}.txt` na pasta escolhida.

```bash
python gui.py
```

### API HTTP

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

## Gerar executável (.exe) no Windows

A forma mais comum na comunidade Python é o **[PyInstaller](https://pyinstaller.org/)**. O alvo recomendado é a **interface gráfica** (`gui.py`), não a API.

### Passos

```powershell
cd AudioTranscriber
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-build.txt
.\build_exe.ps1
```

O executável fica em:

`dist\AudioTranscriber\AudioTranscriber.exe`

Distribua a **pasta inteira** `dist\AudioTranscriber\` (várias DLLs e bibliotecas vêm junto).

**Não execute** arquivos dentro de `build\` — essa pasta é temporária do PyInstaller e causa erro de `python3xx.dll`.

### Erro ao abrir o .exe (`python311.dll` / `LoadLibrary`)

1. Use apenas `dist\AudioTranscriber\AudioTranscriber.exe` (não a pasta `build\`).
2. Copie a pasta `dist\AudioTranscriber\` inteira para o destino (não mova só o `.exe`).
3. Rebuild após atualizar o projeto: `.\build_exe.ps1`
4. Instale o [Visual C++ Redistributable x64](https://aka.ms/vs/17/release/vc_redist.x64.exe) se o erro persistir.

### O que esperar

| Item | Detalhe |
|------|---------|
| Tamanho | Centenas de MB (Whisper + ONNX + dependências) |
| Primeira execução | Baixa o modelo Whisper (internet uma vez) |
| FFmpeg | Instale no PATH **ou** copie `ffmpeg.exe` para a mesma pasta do `.exe` |
| API FastAPI | Não é empacotada por padrão; o foco do `.exe` é a GUI |

### Alternativas

- **--onefile** (um único `.exe`): mais lento ao abrir e mais frágil com libs de ML; `--onedir` é mais estável.
- **[Nuitka](https://nuitka.net/)**: compila para binário nativo; build mais complexo.
- **Instalador** (Inno Setup, WiX): embrulha a pasta `dist` para o usuário final.

### Uso offline do .exe

1. Rode uma vez **com internet** para baixar o modelo.
2. (Opcional) Copie a pasta de cache do Hugging Face para a máquina alvo.
3. Coloque `ffmpeg.exe` ao lado do executável se o PC não tiver FFmpeg no PATH.
