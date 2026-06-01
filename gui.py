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
    ("Personalizado…", "personalizado"),
)

LANGUAGE_CHOICES = ("pt", "en", "es", "fr", "de", "it", "auto")


class TranscriberApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AudioTranscriber")
        self.minsize(540, 520)
        self.resizable(True, True)

        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_name = tk.StringVar()
        self.include_timestamps = tk.BooleanVar(value=True)
        self.quality_preset = tk.StringVar(value="equilibrada")
        self.model_size = tk.StringVar(value="base")
        self.memory_profile = tk.StringVar(value="balanced")
        self.compute_type = tk.StringVar(value="int8")
        self.beam_size = tk.StringVar(value="5")
        self.language = tk.StringVar(value="pt")
        self.progress_text = tk.StringVar(value="")
        self.status = tk.StringVar(value=f"Dispositivo: {DEVICE}")

        self._build_ui()
        self._on_quality_changed()

    def _build_ui(self) -> None:
        padding = {"padx": 12, "pady": 4}
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        files_frame = ttk.LabelFrame(frame, text="Arquivos", padding=8)
        files_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(files_frame, text="Entrada:").grid(row=0, column=0, sticky="w")
        ttk.Entry(files_frame, textvariable=self.input_path, width=48).grid(
            row=1, column=0, sticky="ew", **padding
        )
        ttk.Button(files_frame, text="Escolher…", command=self._pick_input).grid(
            row=1, column=1, **padding
        )

        ttk.Label(files_frame, text="Pasta de saída:").grid(row=2, column=0, sticky="w")
        ttk.Entry(files_frame, textvariable=self.output_dir, width=48).grid(
            row=3, column=0, sticky="ew", **padding
        )
        ttk.Button(files_frame, text="Escolher…", command=self._pick_output).grid(
            row=3, column=1, **padding
        )

        ttk.Label(files_frame, text="Nome do .txt:").grid(row=4, column=0, sticky="w")
        ttk.Entry(files_frame, textvariable=self.output_name, width=48).grid(
            row=5, column=0, sticky="ew", **padding
        )
        ttk.Label(
            files_frame,
            text="(vazio = mesmo nome do áudio)",
            font=("TkDefaultFont", 8),
        ).grid(row=5, column=1, sticky="w")

        files_frame.columnconfigure(0, weight=1)

        cfg_frame = ttk.LabelFrame(frame, text="Qualidade da transcrição", padding=8)
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(cfg_frame, text="Preset:").grid(row=0, column=0, sticky="w")
        quality_combo = ttk.Combobox(
            cfg_frame,
            textvariable=self.quality_preset,
            state="readonly",
            width=42,
        )
        quality_combo["values"] = [label for label, _ in QUALITY_CHOICES]
        quality_combo.grid(row=0, column=1, sticky="ew", **padding)
        quality_combo.bind("<<ComboboxSelected>>", self._on_quality_selected)

        self._quality_labels = {label: key for label, key in QUALITY_CHOICES}
        self._quality_keys = {key: label for label, key in QUALITY_CHOICES}
        self.quality_preset.set(self._quality_keys["equilibrada"])

        self.advanced_frame = ttk.Frame(cfg_frame)
        self.advanced_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
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
        ttk.Combobox(
            self.advanced_frame,
            textvariable=self.language,
            values=LANGUAGE_CHOICES,
            state="readonly",
            width=14,
        ).grid(row=2, column=1, sticky="w", padx=6, pady=2)

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

        self.progress_bar = ttk.Progressbar(
            frame, mode="determinate", maximum=100, length=460
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        ttk.Label(frame, textvariable=self.progress_text).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status, wraplength=500).pack(anchor="w", pady=(4, 0))

    def _on_quality_selected(self, _event=None) -> None:
        label = self.quality_preset.get()
        key = self._quality_labels.get(label, "equilibrada")
        self._on_quality_changed(key)

    def _on_quality_changed(self, preset_key: str | None = None) -> None:
        if preset_key is None:
            label = self.quality_preset.get()
            preset_key = self._quality_labels.get(label, "equilibrada")

        is_custom = preset_key == "personalizado"
        combo_state = "readonly" if is_custom else "disabled"
        for combo in self._preset_combos:
            combo.configure(state=combo_state)

        if not is_custom:
            preset = TranscriptionSettings.from_quality_preset(preset_key)
            self.model_size.set(preset.model_size)
            self.memory_profile.set(preset.memory_profile)
            self.compute_type.set(preset.compute_type)
            self.beam_size.set(str(preset.beam_size or 5))

    def _build_settings(self) -> TranscriptionSettings:
        label = self.quality_preset.get()
        preset_key = self._quality_labels.get(label, "equilibrada")

        if preset_key != "personalizado":
            settings = TranscriptionSettings.from_quality_preset(preset_key)
            settings.language = self.language.get()
            return settings

        beam = int(self.beam_size.get())
        return TranscriptionSettings(
            model_size=self.model_size.get(),
            compute_type=self.compute_type.get(),
            memory_profile=self.memory_profile.get(),
            language=self.language.get(),
            beam_size=beam,
            quality_preset="personalizado",
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

    def _reset_progress(self) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = 0
        self.progress_text.set("")

    def _report_progress(self, ratio: float, message: str | None) -> None:
        def update() -> None:
            if message:
                self.progress_text.set(message)
                self.status.set(message)

            if ratio < 0:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start(12)
                return

            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            percent = int(max(0.0, min(ratio, 1.0)) * 100)
            self.progress_bar["value"] = percent

        self.after(0, update)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.transcribe_btn.configure(state=state)
        if busy:
            self._reset_progress()
        else:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")

    def _start_transcription(self) -> None:
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
        self.status.set(
            f"Modelo: {settings.model_size} | "
            f"Beam: {settings.beam_size or 'auto'} | "
            f"Idioma: {settings.language}"
        )

        thread = threading.Thread(
            target=self._run_transcription,
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

    def _run_transcription(
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
            self.after(0, lambda: self._on_success(output_file))
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _on_success(self, output_file: Path) -> None:
        self._set_busy(False)
        self.progress_bar["value"] = 100
        self.progress_text.set("100% — concluído")
        self.status.set(f"Concluído: {output_file}")
        messagebox.showinfo(
            "Transcrição concluída",
            f"Texto salvo em:\n{output_file}",
        )

    def _on_error(self, detail: str) -> None:
        self._set_busy(False)
        self.status.set("Erro na transcrição.")
        messagebox.showerror("Erro", detail)


def main() -> None:
    app = TranscriberApp()
    app.mainloop()


if __name__ == "__main__":
    main()
