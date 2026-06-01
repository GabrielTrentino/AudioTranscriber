# AudioTranscriber

Transcrição de áudio e vídeo para texto com [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

O projeto oferece:

- **Interface gráfica (GUI)** — `gui.py`, recomendado para uso no dia a dia e para o `.exe` no Windows.
- **API HTTP** — `main.py` (FastAPI), para integração com outros sistemas.

## Estrutura do projeto

| Arquivo / pasta | Função |
|-----------------|--------|
| `gui.py` | Interface tkinter (um arquivo, lote, progresso, cancelar) |
| `main.py` | API REST (`POST /transcribe`, `GET /health`) |
| `transcriber.py` | Whisper, presets, formatação e gravação do `.txt` |
| `build_exe.ps1` | Gera o executável Windows com PyInstaller |
| `requirements.txt` | Dependências de execução |
| `requirements-build.txt` | PyInstaller (somente para build do `.exe`) |
| `TODO.md` | Roadmap de arquitetura (melhorias futuras) |

## Requisitos

- Python 3.10+ (o ambiente de desenvolvimento atual usa 3.14)
- [FFmpeg](https://ffmpeg.org/) no PATH, **ou** `ffmpeg.exe` na mesma pasta do `.exe` / do projeto

## Instalação

```powershell
cd AudioTranscriber
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Interface gráfica (recomendado)

```powershell
python gui.py
```

### Abas de arquivos

- **Um arquivo** — entrada, pasta de saída e nome opcional do `.txt` (vazio = mesmo nome do áudio).
- **Vários arquivos** — lista de áudios/vídeos; cada um gera `{nome-original}.txt` na pasta de saída.

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

| Como você roda | Caminho típico do log |
|----------------|------------------------|
| `python gui.py` | `AudioTranscriber\last_run.log` (pasta do `gui.py`) |
| `.exe` em `dist` | `dist\AudioTranscriber\last_run.log` (ao lado do `.exe`) |
| Fallback | `%USERPROFILE%\AudioTranscriber\last_run.log` |

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

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Documentação interativa: http://127.0.0.1:8000/docs

### Exemplo

```bash
curl -X POST "http://127.0.0.1:8000/transcribe?timestamps=true&quality=equilibrada&language=pt" -F "file=@audio.mp3"
```

Resposta:

```json
{"text": "texto transcrito..."}
```

### Endpoints

- `GET /health` — status da API
- `POST /transcribe` — envia um arquivo (`file`) de áudio ou vídeo

Parâmetros úteis em `POST /transcribe`: `timestamps`, `quality` (`rapida` / `equilibrada` / `alta`), `language`, `model`.

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
pip install -r requirements.txt -r requirements-build.txt
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
| Log | `last_run.log` na pasta do executável |
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
| `pasta de saída não selecionada` | Escolher pasta de saída (compartilhada entre as abas) |
| `lista de lote vazia` | Aba **Vários arquivos** → Adicionar arquivos |

## Roadmap

Melhorias planejadas estão em [`TODO.md`](TODO.md) (pacote modular, testes, CI, mais formatos de saída, etc.).

## Licença

Ver [`LICENSE`](LICENSE).
