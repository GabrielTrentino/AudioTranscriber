import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from transcriber import DEVICE, MODEL_SIZE, transcribe_to_file

AUDIO_VIDEO_TYPES = (
    ("Áudio e vídeo", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.webm *.avi"),
    ("Todos os arquivos", "*.*"),
)


class TranscriberApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AudioTranscriber")
        self.minsize(520, 220)
        self.resizable(True, False)

        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.status = tk.StringVar(
            value=f"Modelo: {MODEL_SIZE} | Dispositivo: {DEVICE}"
        )

        self._build_ui()

    def _build_ui(self) -> None:
        padding = {"padx": 12, "pady": 6}
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Arquivo de entrada:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.input_path, width=50).grid(
            row=1, column=0, sticky="ew", **padding
        )
        ttk.Button(frame, text="Escolher arquivo…", command=self._pick_input).grid(
            row=1, column=1, **padding
        )

        ttk.Label(frame, text="Pasta de saída:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_dir, width=50).grid(
            row=3, column=0, sticky="ew", **padding
        )
        ttk.Button(frame, text="Escolher pasta…", command=self._pick_output).grid(
            row=3, column=1, **padding
        )

        self.transcribe_btn = ttk.Button(
            frame, text="Transcrever", command=self._start_transcription
        )
        self.transcribe_btn.grid(row=4, column=0, columnspan=2, pady=(12, 4))

        ttk.Label(frame, textvariable=self.status, wraplength=480).grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

        frame.columnconfigure(0, weight=1)

    def _pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar áudio ou vídeo",
            filetypes=AUDIO_VIDEO_TYPES,
        )
        if path:
            self.input_path.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Selecionar pasta de saída")
        if path:
            self.output_dir.set(path)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.transcribe_btn.configure(state=state)

    def _start_transcription(self) -> None:
        input_file = self.input_path.get().strip()
        output_folder = self.output_dir.get().strip()

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

        self._set_busy(True)
        self.status.set("Transcrevendo… isso pode levar alguns minutos.")

        thread = threading.Thread(
            target=self._run_transcription,
            args=(input_path, Path(output_folder)),
            daemon=True,
        )
        thread.start()

    def _run_transcription(self, input_path: Path, output_dir: Path) -> None:
        try:
            output_file = transcribe_to_file(input_path, output_dir)
            self.after(
                0,
                lambda: self._on_success(output_file),
            )
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _on_success(self, output_file: Path) -> None:
        self._set_busy(False)
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
