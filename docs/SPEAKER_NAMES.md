# Nomes reais dos falantes (planejado)

Hoje a diarização rotula interlocutores como `SPEAKER_00`, `SPEAKER_01`, … com base no modelo pyannote (Hugging Face). Isso identifica **vozes distintas**, não o **nome** da pessoa.

## Objetivo

Saída legível para legendas, por exemplo:

```
[Maria] [00:12 - 00:18] Olá, tudo bem?
[João] [00:19 - 00:24] Tudo sim, e você?
```

## Abordagem proposta

### 1. Arquivo sidecar `.speakers.json`

Ao lado do `.txt` (mesmo nome base), salvar mapeamento editável:

```json
{
  "SPEAKER_00": "Maria",
  "SPEAKER_01": "João"
}
```

- Gerado automaticamente na 1ª diarização com rótulos genéricos ou vazio.
- Usuário edita nomes no Bloco de Notas ou numa futura tela da GUI.
- Reprocessamento ou exportação SRT/VTT substitui `SPEAKER_XX` pelo nome do JSON.

### 2. Diálogo na GUI (fase 2)

Após a transcrição com falantes:

1. Listar `SPEAKER_00`, `SPEAKER_01`, … detectados.
2. Campos opcionais para digitar o nome de cada um.
3. Salvar `.speakers.json` e regravar o `.txt` com nomes aplicados.

### 3. Pré-definição antes de transcrever (fase 3)

Se o usuário souber quantos falantes há:

- Campos “Falante 1”, “Falante 2”, … (opcional).
- `DIARIZATION_NUM_SPEAKERS=2` melhora a diarização.
- Nomes informados já entram no resultado final.

## Limitações

- pyannote **não** reconhece identidade por nome; só separa vozes.
- Nomes reais dependem sempre de input humano ou cadastro prévio.
- Vozes muito parecidas podem ser agrupadas errado — nomes não corrigem isso.

## Uso hoje (sidecar automático)

1. Transcreva com **Identificar falantes** ativado.
2. Na pasta do `.txt`, será criado `meu_audio.speakers.json`, por exemplo:

```json
{
  "SPEAKER_00": "",
  "SPEAKER_01": ""
}
```

3. Preencha os valores: `"SPEAKER_00": "Maria"`, `"SPEAKER_01": "João"`.
4. Transcreva de novo (mesmo áudio e mesmo nome de saída) — o `.txt` passa a usar os nomes.

## Tarefas técnicas (futuro)

- [x] Escrever/ler `.speakers.json` (`core/speaker_names.py`)
- [x] `format_labeled_segments()` com mapa `speaker → nome`
- [ ] Botão “Editar nomes dos falantes…” na GUI
- [ ] Export SRT/VTT com prefixo de nome
