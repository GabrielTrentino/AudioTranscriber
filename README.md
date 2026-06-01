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

Usa **tkinter** (biblioteca padrão do Python). Escolha o arquivo de entrada, a pasta de saída, o **nome do arquivo de saída** (opcional), marque **Incluir timestamp** se quiser o tempo de cada trecho no texto, e clique em **Transcrever**.

Exemplo com timestamp:

```
[00:00:02 - 00:00:08] Bom dia, vamos começar a reunião.
[00:00:15 - 00:00:22] O primeiro ponto é o orçamento.
```

Durante a transcrição, a barra de progresso avança conforme os trechos do áudio são processados (com base na duração total).

### Qualidade (escolha do usuário)

Na seção **Qualidade da transcrição**:

| Preset | Modelo | Uso |
|--------|--------|-----|
| **Rápida** | `base`, beam 1 | Menos RAM, mais rápido, mais erros |
| **Equilibrada** | `base`, beam 5 | Recomendado para a maioria |
| **Alta qualidade** | `small`, beam 5 | Melhor texto, mais lento e RAM |
| **Personalizado** | Você escolhe modelo, memória, precisão (`int8`/`float16`), beam e idioma |

Idioma `auto` deixa o Whisper detectar automaticamente.

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
curl -X POST "http://127.0.0.1:8000/transcribe?timestamps=true&quality=alta&language=pt" -F "file=@audio.mp3"
```

Resposta:

```json
{"text": "texto transcrito..."}
```

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `WHISPER_QUALITY_PRESET` | — | `rapida`, `equilibrada` ou `alta` (sobrescreve modelo/beam na API/CLI) |
| `WHISPER_MODEL` | `base` | Modelo (`tiny`, `base`, `small`, `medium`, `large-v3`, …) |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda` ou `auto` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` (GPU costuma usar `float16`) |
| `WHISPER_LANGUAGE` | `pt` | Código do idioma |
| `WHISPER_OUTPUT_FORMAT` | `line` | `line` (uma linha por trecho), `time` (com `[MM:SS - MM:SS]`), `none` (texto corrido) |
| `WHISPER_PAUSE_GAP` | `1.5` | Segundos de pausa para inserir linha em branco entre parágrafos |

### Uso de memória

Não há um limite fixo em MB (depende do modelo e do áudio). Use o perfil ou ajuste fino:

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `WHISPER_MEMORY_PROFILE` | `balanced` | `low` (menos RAM), `balanced`, `high` (mais qualidade, mais RAM) |
| `WHISPER_CPU_THREADS` | (do perfil) | Threads na CPU (`0` = automático) |
| `WHISPER_NUM_WORKERS` | `1` | Workers paralelos (mais = mais RAM) |
| `WHISPER_CHUNK_LENGTH` | (do perfil) | Segundos por bloco de áudio (menor = menos pico de RAM em arquivos longos) |
| `WHISPER_BEAM_SIZE` | (do perfil) | `1` usa menos memória; `5` é mais preciso |

Perfil **`low`** (PC com pouca RAM):

```powershell
set WHISPER_MEMORY_PROFILE=low
set WHISPER_MODEL=tiny
set WHISPER_COMPUTE_TYPE=int8
python gui.py
```

Também ajudam: modelo menor (`tiny`/`base`) e `WHISPER_COMPUTE_TYPE=int8`.

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
