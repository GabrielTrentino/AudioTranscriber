import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from transcriber import (
    COMPUTE_OPTIONS,
    DEVICE,
    MEMORY_PROFILE_OPTIONS,
    MODEL_OPTIONS,
    TranscriptionSettings,
    transcribe_to_file,
)

AUDIO_VIDEO_TYPES = (
    ("Áudio e vídeo", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.webm *.avi"),
    ("Todos os arquivos", "*.*"),
)

QUALITY_CHOICES = (
    ("Rápida (menos RAM, mais erros)", "rapida"),
    ("Equilibrada (recomendado)", "equilibrada"),
    ("Alta qualidade (mais lento)", "alta"),
    ("Personalizado", "personalizado"),
)

LANGUAGE_CHOICES = ("pt", "en", "es", "fr", "de", "it", "auto")


class TranscriberApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AudioTranscriber")
        self.minsize(540, 580)
        self.resizable(True, True)

        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_name = tk.StringVar()
        self.include_timestamps = tk.BooleanVar(value=True)
        self.quality_preset = tk.StringVar()
        self.model_size = tk.StringVar(value="base")
        self.memory_profile = tk.StringVar(value="balanced")
        self.compute_type = tk.StringVar(value="int8")
        self.beam_size = tk.StringVar(value="5")
        self.language = tk.StringVar(value="pt")
        self.progress_text = tk.StringVar(value="")
        self.status = tk.StringVar(value=f"Dispositivo: {DEVICE}")

        self._batch_paths: list[str] = []

        self._quality_labels = {label: key for label, key in QUALITY_CHOICES}
        self._quality_keys = {key: label for label, key in QUALITY_CHOICES}

        self._build_ui()
        self.quality_preset.set(self._quality_keys["equilibrada"])
        self._apply_quality_preset("equilibrada")
        self._update_preset_fields_state("equilibrada")

    def _build_ui(self) -> None:
        padding = {"padx": 12, "pady": 4}
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        files_frame = ttk.LabelFrame(frame, text="Arquivos", padding=8)
        files_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))

        self.files_notebook = ttk.Notebook(files_frame)
        self.files_notebook.pack(fill=tk.BOTH, expand=True)

        single_tab = ttk.Frame(self.files_notebook, padding=4)
        batch_tab = ttk.Frame(self.files_notebook, padding=4)
        self.files_notebook.add(single_tab, text="Um arquivo")
        self.files_notebook.add(batch_tab, text="Vários arquivos")

        self._build_single_tab(single_tab, padding)
        self._build_batch_tab(batch_tab, padding)

        cfg_frame = ttk.LabelFrame(frame, text="Qualidade da transcrição", padding=8)
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(cfg_frame, text="Preset:").grid(row=0, column=0, sticky="w")
        self.quality_combo = ttk.Combobox(
            cfg_frame,
            textvariable=self.quality_preset,
            state="readonly",
            width=42,
            values=[label for label, _ in QUALITY_CHOICES],
        )
        self.quality_combo.grid(row=0, column=1, sticky="ew", **padding)
        self.quality_combo.bind("<<ComboboxSelected>>", self._on_quality_selected)

        ttk.Label(
            cfg_frame,
            text="Use Personalizado para alterar modelo, memória, precisão e beam.",
            font=("TkDefaultFont", 8),
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.advanced_frame = ttk.Frame(cfg_frame)
        self.advanced_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._preset_combos: list[ttk.Combobox] = []

        ttk.Label(self.advanced_frame, text="Modelo:").grid(row=0, column=0, sticky="w")
        self._preset_combos.append(
            ttk.Combobox(
                self.advanced_frame,
                textvariable=self.model_size,
                values=MODEL_OPTIONS,
                state="readonly",
                width=14,
            )
        )
        self._preset_combos[-1].grid(row=0, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(self.advanced_frame, text="Memória:").grid(row=0, column=2, sticky="w")
        self._preset_combos.append(
            ttk.Combobox(
                self.advanced_frame,
                textvariable=self.memory_profile,
                values=MEMORY_PROFILE_OPTIONS,
                state="readonly",
                width=12,
            )
        )
        self._preset_combos[-1].grid(row=0, column=3, sticky="w", padx=6, pady=2)

        ttk.Label(self.advanced_frame, text="Precisão:").grid(row=1, column=0, sticky="w")
        self._preset_combos.append(
            ttk.Combobox(
                self.advanced_frame,
                textvariable=self.compute_type,
                values=COMPUTE_OPTIONS,
                state="readonly",
                width=14,
            )
        )
        self._preset_combos[-1].grid(row=1, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(self.advanced_frame, text="Beam:").grid(row=1, column=2, sticky="w")
        self._preset_combos.append(
            ttk.Combobox(
                self.advanced_frame,
                textvariable=self.beam_size,
                values=("1", "3", "5"),
                state="readonly",
                width=12,
            )
        )
        self._preset_combos[-1].grid(row=1, column=3, sticky="w", padx=6, pady=2)

        ttk.Label(self.advanced_frame, text="Idioma:").grid(row=2, column=0, sticky="w")
        self._language_combo = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.language,
            values=LANGUAGE_CHOICES,
            state="readonly",
            width=14,
        )
        self._language_combo.grid(row=2, column=1, sticky="w", padx=6, pady=2)

        cfg_frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            frame,
            text="Incluir timestamp (início - fim de cada trecho)",
            variable=self.include_timestamps,
        ).pack(anchor="w", pady=(0, 8))

        self.transcribe_btn = ttk.Button(
            frame, text="Transcrever", command=self._start_transcription
        )
        self.transcribe_btn.pack(pady=(0, 8))

        progress_frame = ttk.LabelFrame(frame, text="Progresso", padding=8)
        progress_frame.pack(fill=tk.X, pady=(0, 8))

        self.progress_bar = ttk.Progressbar(
            progress_frame, mode="determinate", maximum=100, length=460
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(progress_frame, textvariable=self.progress_text).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status, wraplength=500).pack(anchor="w")

    def _build_single_tab(self, parent: ttk.Frame, padding: dict) -> None:
        ttk.Label(parent, text="Entrada:").grid(row=0, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.input_path, width=48).grid(
            row=1, column=0, sticky="ew", **padding
        )
        ttk.Button(parent, text="Escolher…", command=self._pick_input).grid(
            row=1, column=1, **padding
        )

        ttk.Label(parent, text="Pasta de saída:").grid(row=2, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.output_dir, width=48).grid(
            row=3, column=0, sticky="ew", **padding
        )
        ttk.Button(parent, text="Escolher…", command=self._pick_output).grid(
            row=3, column=1, **padding
        )

        ttk.Label(parent, text="Nome do .txt:").grid(row=4, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.output_name, width=48).grid(
            row=5, column=0, sticky="ew", **padding
        )
        ttk.Label(
            parent,
            text="(vazio = mesmo nome do áudio)",
            font=("TkDefaultFont", 8),
        ).grid(row=5, column=1, sticky="w")

        parent.columnconfigure(0, weight=1)

    def _build_batch_tab(self, parent: ttk.Frame, padding: dict) -> None:
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", **padding)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.batch_listbox = tk.Listbox(
            list_frame,
            height=7,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
        )
        self.batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.batch_listbox.yview)

        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="w", **padding)

        ttk.Button(btn_frame, text="Adicionar arquivos…", command=self._batch_add_files).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Remover selecionados", command=self._batch_remove_selected).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Limpar lista", command=self._batch_clear).pack(side=tk.LEFT)

        ttk.Label(parent, text="Pasta de saída:").grid(row=2, column=0, sticky="w")
        ttk.Entry(parent, textvariable=self.output_dir, width=48).grid(
            row=3, column=0, sticky="ew", **padding
        )
        ttk.Button(parent, text="Escolher…", command=self._pick_output).grid(
            row=3, column=1, **padding
        )

        ttk.Label(
            parent,
            text="Cada arquivo gera um .txt com o mesmo nome (ex.: audio.mp3 → audio.txt).",
            font=("TkDefaultFont", 8),
            wraplength=420,
        ).grid(row=4, column=0, columnspan=2, sticky="w", **padding)

        parent.columnconfigure(0, weight=1)

    def _is_batch_mode(self) -> bool:
        return self.files_notebook.index(self.files_notebook.select()) == 1

    def _batch_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecionar áudios ou vídeos",
            filetypes=AUDIO_VIDEO_TYPES,
        )
        if not paths:
            return

        existing = set(self._batch_paths)
        for path in paths:
            if path not in existing:
                existing.add(path)
                self._batch_paths.append(path)
                self.batch_listbox.insert(tk.END, Path(path).name)

    def _batch_remove_selected(self) -> None:
        selection = list(self.batch_listbox.curselection())
        if not selection:
            return
        for index in reversed(selection):
            self.batch_listbox.delete(index)
            del self._batch_paths[index]

    def _batch_clear(self) -> None:
        self.batch_listbox.delete(0, tk.END)
        self._batch_paths.clear()

    def _on_quality_selected(self, _event=None) -> None:
        label = self.quality_preset.get()
        key = self._quality_labels.get(label, "equilibrada")
        self._apply_quality_preset(key)
        self._update_preset_fields_state(key)

    def _apply_quality_preset(self, preset_key: str) -> None:
        if preset_key == "personalizado":
            return
        preset = TranscriptionSettings.from_quality_preset(preset_key)
        self.model_size.set(preset.model_size)
        self.memory_profile.set(preset.memory_profile)
        self.compute_type.set(preset.compute_type)
        self.beam_size.set(str(preset.beam_size or 5))

    def _update_preset_fields_state(self, preset_key: str) -> None:
        is_custom = preset_key == "personalizado"
        combo_state = "readonly" if is_custom else "disabled"
        for combo in self._preset_combos:
            combo.configure(state=combo_state)

    def _get_preset_key(self) -> str:
        label = self.quality_preset.get()
        return self._quality_labels.get(label, "equilibrada")

    def _build_settings(self) -> TranscriptionSettings:
        preset_key = self._get_preset_key()

        if preset_key != "personalizado":
            settings = TranscriptionSettings.from_quality_preset(preset_key)
            settings.language = self.language.get()
            return settings

        return TranscriptionSettings(
            model_size=self.model_size.get(),
            compute_type=self.compute_type.get(),
            memory_profile=self.memory_profile.get(),
            language=self.language.get(),
            beam_size=int(self.beam_size.get()),
            quality_preset="personalizado",
        )

    def _update_config_status(self, settings: TranscriptionSettings) -> None:
        self.status.set(
            f"Modelo: {settings.model_size} | "
            f"Memória: {settings.memory_profile} | "
            f"Precisão: {settings.compute_type} | "
            f"Beam: {settings.beam_size} | "
            f"Idioma: {settings.language}"
        )

    def _pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar áudio ou vídeo",
            filetypes=AUDIO_VIDEO_TYPES,
        )
        if path:
            self.input_path.set(path)
            if not self.output_name.get().strip():
                self.output_name.set(Path(path).stem)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Selecionar pasta de saída")
        if path:
            self.output_dir.set(path)

    def _refresh_progress_ui(self) -> None:
        self.progress_bar.update_idletasks()
        self.update_idletasks()

    def _show_progress_indeterminate(self, message: str) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start(10)
        self.progress_text.set(message)
        self._refresh_progress_ui()

    def _show_progress_percent(self, percent: int, message: str | None) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = percent
        if message:
            self.progress_text.set(message)
        else:
            self.progress_text.set(f"Transcrevendo… {percent}%")
        self._refresh_progress_ui()

    def _reset_progress(self) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = 0
        self.progress_text.set("")
        self._refresh_progress_ui()

    def _report_progress(self, ratio: float, message: str | None) -> None:
        def update() -> None:
            if ratio < 0:
                self._show_progress_indeterminate(message or "Processando…")
                return

            percent = int(max(0.0, min(ratio, 1.0)) * 100)
            self._show_progress_percent(percent, message)

        self.after(0, update)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.transcribe_btn.configure(state=state)
        self.quality_combo.configure(state="disabled" if busy else "readonly")
        self.files_notebook.configure(state="disabled" if busy else "normal")
        if busy:
            self._update_preset_fields_state(self._get_preset_key())
            for combo in self._preset_combos:
                combo.configure(state="disabled")
            self._language_combo.configure(state="disabled")
        else:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.quality_combo.configure(state="readonly")
            self._language_combo.configure(state="readonly")
            self._update_preset_fields_state(self._get_preset_key())

    def _start_transcription(self) -> None:
        if self._is_batch_mode():
            self._start_batch_transcription()
        else:
            self._start_single_transcription()

    def _start_single_transcription(self) -> None:
        input_file = self.input_path.get().strip()
        output_folder = self.output_dir.get().strip()
        output_name = self.output_name.get().strip() or None

        if not input_file:
            messagebox.showwarning("Atenção", "Selecione um arquivo de entrada.")
            return
        if not output_folder:
            messagebox.showwarning("Atenção", "Selecione uma pasta de saída.")
            return

        input_path = Path(input_file)
        if not input_path.is_file():
            messagebox.showerror("Erro", "Arquivo de entrada não encontrado.")
            return

        settings = self._build_settings()
        self._set_busy(True)
        self._update_config_status(settings)
        self._show_progress_indeterminate("Preparando…")

        thread = threading.Thread(
            target=self._run_single_transcription,
            args=(
                input_path,
                Path(output_folder),
                output_name,
                settings,
                self.include_timestamps.get(),
            ),
            daemon=True,
        )
        thread.start()

    def _start_batch_transcription(self) -> None:
        output_folder = self.output_dir.get().strip()

        if not self._batch_paths:
            messagebox.showwarning("Atenção", "Adicione pelo menos um arquivo à lista.")
            return
        if not output_folder:
            messagebox.showwarning("Atenção", "Selecione uma pasta de saída.")
            return

        paths = [Path(p) for p in self._batch_paths]
        missing = [p.name for p in paths if not p.is_file()]
        if missing:
            messagebox.showerror(
                "Erro",
                "Arquivos não encontrados:\n" + "\n".join(missing[:10]),
            )
            return

        settings = self._build_settings()
        self._set_busy(True)
        self._update_config_status(settings)
        self._show_progress_indeterminate("Preparando lote…")

        thread = threading.Thread(
            target=self._run_batch_transcription,
            args=(
                paths,
                Path(output_folder),
                settings,
                self.include_timestamps.get(),
            ),
            daemon=True,
        )
        thread.start()

    def _run_single_transcription(
        self,
        input_path: Path,
        output_dir: Path,
        output_name: str | None,
        settings: TranscriptionSettings,
        include_timestamps: bool,
    ) -> None:
        try:
            output_file = transcribe_to_file(
                input_path,
                output_dir,
                output_name,
                settings=settings,
                include_timestamps=include_timestamps,
                on_progress=self._report_progress,
            )
            self.after(0, lambda: self._on_single_success(output_file))
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _run_batch_transcription(
        self,
        paths: list[Path],
        output_dir: Path,
        settings: TranscriptionSettings,
        include_timestamps: bool,
    ) -> None:
        total = len(paths)
        saved: list[Path] = []
        errors: list[str] = []

        try:
            for index, input_path in enumerate(paths):
                file_label = input_path.name

                def file_progress(
                    ratio: float,
                    message: str | None,
                    *,
                    idx=index,
                    label=file_label,
                ) -> None:
                    overall = (idx + max(0.0, min(ratio, 1.0))) / total
                    if message and "%" in message:
                        detail = message
                    elif ratio >= 0:
                        detail = f"{int(ratio * 100)}%"
                    else:
                        detail = message or "…"
                    self._report_progress(
                        overall,
                        f"Arquivo {idx + 1}/{total}: {label} — {detail}",
                    )

                try:
                    output_file = transcribe_to_file(
                        input_path,
                        output_dir,
                        output_name=None,
                        settings=settings,
                        include_timestamps=include_timestamps,
                        on_progress=file_progress,
                    )
                    saved.append(output_file)
                except Exception as exc:
                    errors.append(f"{file_label}: {exc}")

            self.after(
                0,
                lambda: self._on_batch_finished(saved, errors, output_dir),
            )
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _on_single_success(self, output_file: Path) -> None:
        self._set_busy(False)
        self._show_progress_percent(100, "Concluído (100%)")
        self.status.set(f"Arquivo salvo em: {output_file}")
        messagebox.showinfo(
            "Transcrição concluída",
            f"Texto salvo em:\n{output_file}",
        )

    def _on_batch_finished(
        self,
        saved: list[Path],
        errors: list[str],
        output_dir: Path,
    ) -> None:
        self._set_busy(False)
        self._show_progress_percent(100, None)

        ok_count = len(saved)
        err_count = len(errors)

        if err_count == 0:
            self.progress_text.set(f"Concluído — {ok_count} arquivo(s)")
            self.status.set(f"Pasta de saída: {output_dir}")
            messagebox.showinfo(
                "Lote concluído",
                f"{ok_count} transcrição(ões) salva(s) em:\n{output_dir}",
            )
            return

        self.progress_text.set(f"Concluído — {ok_count} ok, {err_count} erro(s)")
        self.status.set(f"Pasta: {output_dir}")
        detail = "\n".join(errors[:8])
        if len(errors) > 8:
            detail += f"\n… e mais {len(errors) - 8} erro(s)"
        messagebox.showwarning(
            "Lote finalizado com erros",
            f"Sucesso: {ok_count}\nFalhas: {err_count}\n\n{detail}",
        )

    def _on_error(self, detail: str) -> None:
        self._set_busy(False)
        self.progress_text.set("")
        self.status.set(f"Erro: {detail}")
        messagebox.showerror("Erro", detail)


def main() -> None:
    app = TranscriberApp()
    app.mainloop()


if __name__ == "__main__":
    main()
