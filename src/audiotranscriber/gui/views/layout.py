"""Montagem dos widgets tkinter (somente UI, sem lógica Whisper)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from audiotranscriber.core.constants import (
    COMPUTE_OPTIONS,
    MEMORY_PROFILE_OPTIONS,
    MODEL_OPTIONS,
)
from audiotranscriber.gui.constants import LANGUAGE_CHOICES, QUALITY_CHOICES


def build_main_layout(app) -> None:
    """Preenche widgets no `app` (TranscriberApp)."""
    padding = {"padx": 12, "pady": 4}
    frame = ttk.Frame(app, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    files_frame = ttk.LabelFrame(frame, text="Arquivos", padding=8)
    files_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))

    app.files_notebook = ttk.Notebook(files_frame)
    app.files_notebook.pack(fill=tk.BOTH, expand=True)

    single_tab = ttk.Frame(app.files_notebook, padding=4)
    batch_tab = ttk.Frame(app.files_notebook, padding=4)
    app.files_notebook.add(single_tab, text="Um arquivo")
    app.files_notebook.add(batch_tab, text="Vários arquivos")

    build_single_tab(app, single_tab, padding)
    build_batch_tab(app, batch_tab, padding)

    progress_frame = ttk.LabelFrame(frame, text="Progresso", padding=8)
    progress_frame.pack(fill=tk.X, pady=(0, 8))

    app.progress_bar = ttk.Progressbar(
        progress_frame, mode="determinate", maximum=100, length=460
    )
    app.progress_bar.pack(fill=tk.X, pady=(0, 6))
    ttk.Label(progress_frame, textvariable=app.progress_text).pack(anchor="w")

    build_quality_section(app, frame, padding)

    actions_frame = ttk.Frame(frame)
    actions_frame.pack(fill=tk.X, pady=(0, 8))

    app.transcribe_btn = ttk.Button(
        actions_frame, text="Transcrever", command=app._start_transcription
    )
    app.transcribe_btn.pack(side=tk.LEFT)

    app.cancel_btn = ttk.Button(
        actions_frame,
        text="Cancelar",
        command=app._cancel_transcription,
        state=tk.DISABLED,
    )
    app.cancel_btn.pack(side=tk.LEFT, padx=(8, 0))

    ttk.Label(frame, textvariable=app.status, wraplength=500).pack(
        anchor="w", pady=(0, 4)
    )


def build_single_tab(app, parent: ttk.Frame, padding: dict) -> None:
    ttk.Label(parent, text="Entrada:").grid(row=0, column=0, sticky="w")
    app.input_entry = ttk.Entry(parent, textvariable=app.input_path, width=48)
    app.input_entry.grid(row=1, column=0, sticky="ew", **padding)
    ttk.Button(parent, text="Escolher…", command=app._pick_input).grid(
        row=1, column=1, **padding
    )

    ttk.Label(parent, text="Pasta de saída:").grid(row=2, column=0, sticky="w")
    app.output_entry = ttk.Entry(parent, textvariable=app.output_dir, width=48)
    app.output_entry.grid(row=3, column=0, sticky="ew", **padding)
    ttk.Button(parent, text="Escolher…", command=app._pick_output).grid(
        row=3, column=1, **padding
    )

    ttk.Label(parent, text="Nome do .txt:").grid(row=4, column=0, sticky="w")
    app.output_name_entry = ttk.Entry(
        parent, textvariable=app.output_name, width=48
    )
    app.output_name_entry.grid(row=5, column=0, sticky="ew", **padding)
    ttk.Label(
        parent,
        text="(vazio = mesmo nome do áudio; pasta vazia = pasta do arquivo)",
        font=("TkDefaultFont", 8),
        wraplength=200,
    ).grid(row=5, column=1, sticky="w")

    parent.columnconfigure(0, weight=1)


def build_batch_tab(app, parent: ttk.Frame, padding: dict) -> None:
    list_frame = ttk.Frame(parent)
    list_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", **padding)

    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app.batch_listbox = tk.Listbox(
        list_frame,
        height=7,
        selectmode=tk.EXTENDED,
        yscrollcommand=scrollbar.set,
    )
    app.batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=app.batch_listbox.yview)

    btn_frame = ttk.Frame(parent)
    btn_frame.grid(row=1, column=0, columnspan=2, sticky="w", **padding)

    ttk.Button(
        btn_frame, text="Adicionar arquivos…", command=app._batch_add_files
    ).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(
        btn_frame, text="Remover selecionados", command=app._batch_remove_selected
    ).pack(side=tk.LEFT, padx=(0, 6))
    ttk.Button(btn_frame, text="Limpar lista", command=app._batch_clear).pack(
        side=tk.LEFT
    )

    ttk.Label(parent, text="Pasta de saída:").grid(row=2, column=0, sticky="w")
    app.batch_output_entry = ttk.Entry(
        parent, textvariable=app.output_dir, width=48
    )
    app.batch_output_entry.grid(row=3, column=0, sticky="ew", **padding)
    ttk.Button(parent, text="Escolher…", command=app._pick_output).grid(
        row=3, column=1, **padding
    )

    ttk.Label(
        parent,
        text=(
            "Cada arquivo gera um .txt com o mesmo nome (ex.: audio.mp3 → audio.txt). "
            "Pasta de saída vazia = salvar na pasta de cada arquivo."
        ),
        font=("TkDefaultFont", 8),
        wraplength=420,
    ).grid(row=4, column=0, columnspan=2, sticky="w", **padding)

    parent.columnconfigure(0, weight=1)


def build_quality_section(app, frame: ttk.Frame, padding: dict) -> None:
    cfg_frame = ttk.LabelFrame(frame, text="Qualidade da transcrição", padding=8)
    cfg_frame.pack(fill=tk.X, pady=(0, 8))

    ttk.Label(cfg_frame, text="Preset:").grid(row=0, column=0, sticky="w")
    app.quality_combo = ttk.Combobox(
        cfg_frame,
        textvariable=app.quality_preset,
        state="readonly",
        width=42,
        values=[label for label, _ in QUALITY_CHOICES],
    )
    app.quality_combo.grid(row=0, column=1, sticky="ew", **padding)
    app.quality_combo.bind("<<ComboboxSelected>>", app._on_quality_selected)

    ttk.Label(
        cfg_frame,
        text="Use Personalizado para alterar modelo, memória, precisão e beam.",
        font=("TkDefaultFont", 8),
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    app.advanced_frame = ttk.Frame(cfg_frame)
    app.advanced_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    app._preset_combos: list[ttk.Combobox] = []

    ttk.Label(app.advanced_frame, text="Modelo:").grid(row=0, column=0, sticky="w")
    app._preset_combos.append(
        ttk.Combobox(
            app.advanced_frame,
            textvariable=app.model_size,
            values=MODEL_OPTIONS,
            state="readonly",
            width=14,
        )
    )
    app._preset_combos[-1].grid(row=0, column=1, sticky="w", padx=6, pady=2)

    ttk.Label(app.advanced_frame, text="Memória:").grid(row=0, column=2, sticky="w")
    app._preset_combos.append(
        ttk.Combobox(
            app.advanced_frame,
            textvariable=app.memory_profile,
            values=MEMORY_PROFILE_OPTIONS,
            state="readonly",
            width=12,
        )
    )
    app._preset_combos[-1].grid(row=0, column=3, sticky="w", padx=6, pady=2)

    ttk.Label(app.advanced_frame, text="Precisão:").grid(row=1, column=0, sticky="w")
    app._preset_combos.append(
        ttk.Combobox(
            app.advanced_frame,
            textvariable=app.compute_type,
            values=COMPUTE_OPTIONS,
            state="readonly",
            width=14,
        )
    )
    app._preset_combos[-1].grid(row=1, column=1, sticky="w", padx=6, pady=2)

    ttk.Label(app.advanced_frame, text="Beam:").grid(row=1, column=2, sticky="w")
    app._preset_combos.append(
        ttk.Combobox(
            app.advanced_frame,
            textvariable=app.beam_size,
            values=("1", "3", "5"),
            state="readonly",
            width=12,
        )
    )
    app._preset_combos[-1].grid(row=1, column=3, sticky="w", padx=6, pady=2)

    ttk.Label(app.advanced_frame, text="Idioma:").grid(row=2, column=0, sticky="w")
    app._language_combo = ttk.Combobox(
        app.advanced_frame,
        textvariable=app.language,
        values=LANGUAGE_CHOICES,
        state="readonly",
        width=14,
    )
    app._language_combo.grid(row=2, column=1, sticky="w", padx=6, pady=2)

    cfg_frame.columnconfigure(1, weight=1)

    options_frame = ttk.Frame(frame)
    options_frame.pack(fill=tk.X, pady=(0, 8))

    ttk.Checkbutton(
        options_frame,
        text="Incluir [início - fim]",
        variable=app.include_timestamps,
    ).pack(anchor="w")

    app.identify_speakers_btn = ttk.Checkbutton(
        options_frame,
        text="Identificar falantes (pyannote / Hugging Face)",
        variable=app.identify_speakers,
    )
    app.identify_speakers_btn.pack(anchor="w", pady=(4, 0))
