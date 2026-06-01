# AudioTranscriber

Transcrição de áudio e vídeo para texto com [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

O projeto oferece:

- **Interface gráfica (GUI)** — `gui.py` ou `audiotranscriber-gui`
- **API HTTP** — `audiotranscriber-api` (FastAPI)
- **CLI** — `python -m audiotranscriber`

## Estrutura do projeto

Código em `src/audiotranscriber/`. Raiz enxuta; detalhes: [`docs/PROJECT_LAYOUT.md`](docs/PROJECT_LAYOUT.md).

**Na raiz:** `README.md`, `LICENSE`, `pyproject.toml`, `requirements.txt`, `gui.py`, `build_exe.ps1`

| Pasta / arquivo | Função |
|-----------------|--------|
| `src/audiotranscriber/` | Pacote principal (gui, api, core, services) |
| `docs/` | `PROJECT_LAYOUT.md`, `ARCHITECTURE.md`, `TODO.md` |
| `config/` | `config.yaml.example` |
| `docker/` | API headless (Dockerfile, compose) |
| `scripts/` | Build PyInstaller, shim legado opcional |

## Requisitos

- Python 3.10+ (o ambiente de desenvolvimento atual usa 3.14)
- [FFmpeg](https://ffmpeg.org/) no PATH, **ou** `ffmpeg.exe` na mesma pasta do `.exe` / do projeto

## Instalação

```powershell
cd AudioTranscriber
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

Opcional: copie `config/config.yaml.example` para `config.yaml` na raiz (device, idioma, API, etc.).

## Linha de comando (CLI)

```powershell
python -m audiotranscriber transcribe audio.mp3 -o ./saida --format srt --quality equilibrada
python -m audiotranscriber batch a.mp3 b.mp4 -o ./saida --format json
python -m audiotranscriber queue jobs.json a.mp3 b.mp4 --run
```

Formatos: `txt`, `srt`, `vtt`, `json`. Diarização: `pip install "audiotranscriber[diarization]"` e `--diarize`.

## Interface gráfica (recomendado)

```powershell
python gui.py
```

### Abas de arquivos

- **Um arquivo** — entrada, pasta de saída (opcional) e nome opcional do `.txt`.
  - Pasta de saída **vazia** → o `.txt` é salvo na **mesma pasta do arquivo de entrada**.
  - Nome do `.txt` **vazio** → mesmo nome do áudio (ex.: `video.mp4` → `video.txt`).
- **Vários arquivos** — lista de áudios/vídeos; cada um gera `{nome-original}.txt`.
  - Pasta de saída **vazia** → cada `.txt` na pasta do respectivo arquivo de entrada.
  - Pasta de saída **preenchida** → todos os `.txt` vão para essa pasta.

### Qualidade da transcrição

| Preset | Modelo | Memória | Observação |
|--------|--------|---------|------------|
| **Rápida** | `base`, beam 1 | `low` | Menos RAM, mais rápido |
| **Equilibrada** | `base`, beam 5 | `balanced` | Recomendado |
| **Alta qualidade** | `small`, beam 5 | `high` | Melhor texto, mais lento |
| **Personalizado** | Você define modelo, memória, precisão (`int8`/`float16`), beam e idioma | — | Só neste preset os campos avançados ficam editáveis |

O idioma pode ser `pt`, `en`, `es`, etc., ou **`auto`** para detecção automática.

### Timestamps

Marque **Incluir timestamp** para gravar início e fim de cada trecho:

```text
[00:00:02 - 00:00:08] Bom dia, vamos começar a reunião.
[00:00:15 - 00:00:22] O primeiro ponto é o orçamento.
```

### Progresso e cancelamento

- A seção **Progresso** (acima das opções de qualidade) mostra a barra e o status da execução (`0%`, carregamento do modelo, `Transcrevendo… X%`).
- O botão **Cancelar** interrompe a transcrição atual (cooperativo: pode levar alguns segundos durante o carregamento do modelo).
- Atualizações da interface usam fila na thread principal, para funcionar de forma confiável no Windows.

### Diagnóstico: `last_run.log`

A cada clique em **Transcrever**, o app recria um log com **apenas a última execução**:

| Situação | Caminho do log |
|----------|----------------|
| Um arquivo | Mesma pasta do `.txt` (pasta de saída ou pasta do áudio) |
| Lote com pasta de saída | Dentro da pasta de saída escolhida |
| Lote sem pasta de saída | Pasta do primeiro arquivo da lista |
| Fallback (pasta não gravável) | Ao lado do `.exe` ou `%USERPROFILE%\AudioTranscriber\` |

Exemplo de conteúdo:

```text
=== AudioTranscriber — última execução (2026-05-31 23:16:11) ===
Botão Transcrever clicado
Modo: um arquivo
Entrada: C:\...\video.mp4
Saída: C:\...\Downloads
Config: preset=equilibrada, modelo=base, idioma=pt
job 1: validação OK, preparando UI
job 1: iniciando worker
job 1: thread de transcrição iniciada
job 1: transcribe video.mp4 -> C:\...\Downloads
job 1: done C:\...\Downloads\video.txt
```

Se o log parar antes de `iniciando worker`, veja a seção [Solução de problemas](#solução-de-problemas).

## API HTTP

Por padrão escuta em **127.0.0.1** (apenas máquina local):

```powershell
audiotranscriber-api
# ou: uvicorn audiotranscriber.api.app:app --host 127.0.0.1 --port 8000
```

Documentação: http://127.0.0.1:8000/docs

Segurança opcional via `API_KEY` (header `X-Api-Key`). CORS: `CORS_ORIGINS`. Rate limit: `API_RATE_LIMIT` / `API_RATE_WINDOW`.

### Docker (API headless)

```powershell
docker compose -f docker/docker-compose.yml up --build
```

### Exemplo

```bash
curl -X POST "http://127.0.0.1:8000/transcribe?timestamps=true&quality=equilibrada&export_format=srt" -F "file=@audio.mp3"
```

### Endpoints

- `GET /health` — status da API
- `POST /transcribe` — envia um arquivo (`file`) de áudio ou vídeo

Parâmetros: `timestamps`, `quality`, `language`, `model`, `export_format` (`txt` / `srt` / `vtt` / `json`).

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `WHISPER_QUALITY_PRESET` | — | `rapida`, `equilibrada` ou `alta` |
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3`, … |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda` ou `auto` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` |
| `WHISPER_LANGUAGE` | `pt` | Código do idioma |
| `WHISPER_OUTPUT_FORMAT` | `line` | `line`, `time`, `none` |
| `WHISPER_PAUSE_GAP` | `1.5` | Pausa (s) para linha em branco entre trechos |
| `WHISPER_MEMORY_PROFILE` | `balanced` | `low`, `balanced`, `high` |
| `WHISPER_CPU_THREADS` | (do perfil) | Threads CPU (`0` = automático) |
| `WHISPER_NUM_WORKERS` | `1` | Workers paralelos |
| `WHISPER_CHUNK_LENGTH` | (do perfil) | Tamanho do bloco em segundos |
| `WHISPER_BEAM_SIZE` | (do perfil) | `1` = menos RAM; `5` = mais preciso |

### PC com pouca RAM

```powershell
$env:WHISPER_MEMORY_PROFILE = "low"
$env:WHISPER_MODEL = "tiny"
$env:WHISPER_COMPUTE_TYPE = "int8"
python gui.py
```

### GPU (exemplo)

```powershell
$env:WHISPER_DEVICE = "cuda"
$env:WHISPER_COMPUTE_TYPE = "float16"
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Gerar executável (.exe) no Windows

Build com **[PyInstaller](https://pyinstaller.org/)** via `build_exe.ps1` (modo `--onedir`, sem UPX).

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt -r scripts/requirements-build.txt
.\build_exe.ps1
```

Saída:

`dist\AudioTranscriber\AudioTranscriber.exe`

Distribua a **pasta inteira** `dist\AudioTranscriber\`. **Não** execute nada em `build\` (pasta temporária do PyInstaller).

| Item | Detalhe |
|------|---------|
| Tamanho | Centenas de MB (Whisper + ONNX + dependências) |
| Primeira execução | Download do modelo Whisper (internet uma vez) |
| FFmpeg | PATH do sistema **ou** `ffmpeg.exe` ao lado do `.exe` |
| Log | `last_run.log` na pasta de saída do `.txt` |
| API | Não vai no `.exe` por padrão; foco na GUI |

### Uso offline do .exe

1. Rode uma vez **com internet** para baixar o modelo.
2. (Opcional) Copie o cache do Hugging Face para a máquina alvo.
3. Coloque `ffmpeg.exe` na pasta `dist\AudioTranscriber\` se não houver FFmpeg no PATH.

## Solução de problemas

### Transcrição não inicia / log para em "Saída"

**Causa corrigida:** o `ttk.Notebook` (abas Um arquivo / Vários) **não suporta** `state="disabled"` no Windows. Isso gerava `TclError: unknown option "-state"` e interrompia o fluxo antes de iniciar o worker.

**Solução:** use a versão atual do projeto (campos desabilitados individualmente, sem desabilitar o notebook). Confirme no `last_run.log` as linhas `iniciando worker` e `thread de transcrição iniciada`.

### Barra de progresso parada em 0%

- Na **primeira execução**, pode ficar vários minutos em "Carregando modelo…" (download + carga) — é normal.
- O heartbeat no log/UI mostra `(aguarde, 2s)`, `(aguarde, 4s)`, etc.
- Se nunca passar de 0% mesmo em áudio curto já com modelo em cache, abra `last_run.log` e verifique erros.

### Erro ao abrir o `.exe` (`python3xx.dll` / `LoadLibrary`)

1. Use só `dist\AudioTranscriber\AudioTranscriber.exe` (não `build\`).
2. Copie a pasta `dist\AudioTranscriber\` inteira.
3. Rebuild: `.\build_exe.ps1`
4. Instale o [Visual C++ Redistributable x64](https://aka.ms/vs/17/release/vc_redist.x64.exe) se necessário.

### FFmpeg / vídeo sem áudio

- Instale FFmpeg ou copie `ffmpeg.exe` para a pasta do app.
- Erros aparecem no `last_run.log` e em uma caixa de diálogo (com caminho do log).

### Abortado no log (sem transcrição)

| Mensagem no log | O que fazer |
|-----------------|-------------|
| `nenhum arquivo de entrada` | Aba **Um arquivo** → Escolher entrada |
| `lista de lote vazia` | Aba **Vários arquivos** → Adicionar arquivos |

A pasta de saída é **opcional**. Se ficar em branco, o app usa a pasta do arquivo de entrada (em lote: a pasta de cada arquivo).

## Roadmap

Melhorias planejadas estão em [`docs/TODO.md`](docs/TODO.md).

## Licença

Ver [`LICENSE`](LICENSE).
