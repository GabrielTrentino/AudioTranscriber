# AudioTranscriber — TODO de arquitetura

Roadmap de melhorias identificadas na revisão de arquitetura (engenharia sênior).  
Prioridade: **P0** crítico → **P2** desejável.

---

## P0 — Estrutura e manutenibilidade

- [x] Reorganizar em pacote (`src/audiotranscriber/`): `core/`, `services/`, `api/`, `gui/`, `config/`
- [x] Quebrar `gui.py` em views + controller (sem lógica Whisper na UI)
- [x] Extrair `TranscriptionService` (modelo, transcrição, gravação)
- [x] Substituir singleton global por `ModelManager` com cache e lock (API concorrente)
- [x] Configuração unificada (`AppConfig`: env + opcional `config.yaml`)
- [x] Documentar ou aplanar pasta `AudioTranscriber/AudioTranscriber/` após clone

## P1 — Paridade, robustez e UX

- [ ] API alinhada à GUI: `memory_profile`, `compute_type`, `beam_size`, lote
- [ ] Validação na borda: FFmpeg, extensão, tamanho máximo, pasta gravável
- [ ] Contrato de progresso tipado (`ProgressEvent`) em vez de `ratio=-1` mágico
- [x] Cancelamento de transcrição (GUI + flag no serviço)
- [ ] Logging estruturado (`logging` + arquivo opcional)
- [ ] Erros de domínio (`FfmpegNotFoundError`, `ModelLoadError`, etc.)
- [ ] Limites na API: upload, timeout, fila configurável

## P1 — Qualidade de engenharia

- [ ] Testes `pytest` (formatter, settings, filenames, mocks do Whisper)
- [ ] CI (GitHub Actions): `ruff`, testes, smoke import
- [ ] `pyproject.toml` com entry points e extras `[dev]` / `[build]`
- [ ] `mypy` / `pyright` no CI
- [ ] Persistir preferências do usuário (`%APPDATA%/AudioTranscriber/settings.json`)

## P2 — Produto e escala

- [x] CLI (`python -m audiotranscriber …`)
- [x] Saída `.srt` / `.vtt` / JSON com segmentos
- [x] Fila de jobs com retomada (lote longo)
- [x] Diarização opcional (WhisperX / pyannote) como extra
- [x] Checagem de dependências no startup do `.exe`
- [x] `docs/ARCHITECTURE.md` com diagramas
- [x] Docker para API headless

## P2 — Segurança (se API exposta na rede)

- [x] Auth ou bind apenas em `127.0.0.1` por padrão
- [x] Rate limiting e CORS explícito

---

## Ordem sugerida

1. Pacote + `TranscriptionService` + `ModelManager`
2. Refatorar GUI
3. API + validações + logging
4. Testes + CI + `pyproject.toml`
5. Cancelamento, prefs, formatos extras

---

## Feito / em andamento

- [x] Barra de progresso visível (fila thread-safe, 0% e status na thread principal)
- [x] Presets travados; **Personalizado** desbloqueia modelo, memória, precisão e beam
