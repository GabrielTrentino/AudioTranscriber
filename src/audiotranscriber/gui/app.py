import queue
import sys
import threading
import time
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from audiotranscriber.core.exceptions import TranscriptionCancelled
from audiotranscriber.core.startup_checks import (
    format_issues,
    has_blocking_errors,
    run_startup_checks,
)
from audiotranscriber.core.settings import TranscriptionSettings
from audiotranscriber.gui.constants import AUDIO_VIDEO_TYPES, QUALITY_CHOICES
from audiotranscriber.gui.controller import QualityFormState, TranscriptionController
from audiotranscriber.gui.views.layout import build_main_layout


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
        self.identify_speakers = tk.BooleanVar(value=False)
        self.quality_preset = tk.StringVar()
        self.model_size = tk.StringVar(value="base")
        self.memory_profile = tk.StringVar(value="balanced")
        self.compute_type = tk.StringVar(value="int8")
        self.beam_size = tk.StringVar(value="5")
        self.language = tk.StringVar(value="pt")
        self.progress_text = tk.StringVar(value="")
        self._controller = TranscriptionController()
        self.status = tk.StringVar(value=f"Dispositivo: {self._controller.device}")

        self._batch_paths: list[str] = []
        self._progress_queue: queue.SimpleQueue = queue.SimpleQueue()
        self._cancel_event = threading.Event()
        self._job_id = 0
        self._progress_started_at: float | None = None
        self._progress_timer_after: str | None = None
        self._progress_ratio: float = 0.0
        self._progress_raw_message: str | None = None
        self._progress_model_label: str = "base"
        self._last_shown_percent: int = -1
        self._last_shown_elapsed: int = -1
        self._active_log_path: Path | None = None

        self._quality_labels = {label: key for label, key in QUALITY_CHOICES}
        self._quality_keys = {key: label for label, key in QUALITY_CHOICES}

        build_main_layout(self)
        self.after(50, self._poll_ui_queue)
        self.quality_preset.set(self._quality_keys["equilibrada"])
        self._apply_quality_preset("equilibrada")
        self._update_preset_fields_state("equilibrada")

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
        return QualityFormState(
            quality_preset_label=self.quality_preset.get(),
            quality_labels=self._quality_labels,
            model_size=self.model_size.get(),
            memory_profile=self.memory_profile.get(),
            compute_type=self.compute_type.get(),
            beam_size=self.beam_size.get(),
            language=self.language.get(),
        ).build_settings()

    def _app_root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[3]

    def _run_log_fallback_candidates(self) -> list[Path]:
        """Usado só se a pasta de saída não for gravável."""
        roots: list[Path] = []
        if getattr(sys, "frozen", False):
            roots.append(Path(sys.executable).resolve().parent)
            roots.append(Path.cwd())
        else:
            roots.append(self._app_root())
        roots.append(Path.cwd())
        roots.append(Path.home() / "AudioTranscriber")

        seen: set[Path] = set()
        candidates: list[Path] = []
        for root in roots:
            path = (root / "last_run.log").resolve()
            if path not in seen:
                seen.add(path)
                candidates.append(path)
        return candidates

    def _run_log_candidates(self, output_dir: Path | None = None) -> list[Path]:
        candidates: list[Path] = []
        if output_dir is not None:
            candidates.append((output_dir.resolve() / "last_run.log"))
        candidates.extend(self._run_log_fallback_candidates())
        return candidates

    def _run_log_path(self) -> Path:
        if self._active_log_path is not None:
            return self._active_log_path
        return self._run_log_fallback_candidates()[0]

    def _reset_run_log(self, output_dir: Path | None = None) -> None:
        """Substitui o log na pasta de saída (ou fallback se não for gravável)."""
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"=== AudioTranscriber — última execução ({started}) ===\n"
        self._active_log_path = None
        errors: list[str] = []

        for path in self._run_log_candidates(output_dir):
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(header, encoding="utf-8")
                self._active_log_path = path
                return
            except OSError as exc:
                errors.append(f"{path} ({exc})")

        detail = errors[0] if errors else "erro desconhecido"
        self.status.set(f"Não foi possível criar last_run.log: {detail}")

    def _log(self, message: str) -> None:
        if self._active_log_path is None:
            self._reset_run_log()
        path = self._active_log_path
        if path is None:
            return
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(message.rstrip() + "\n")
                handle.flush()
        except OSError as exc:
            self.status.set(f"Erro ao gravar log em {path}: {exc}")

    def _update_config_status(self, settings: TranscriptionSettings) -> None:
        self.status.set(
            f"Modelo: {settings.model_size} | "
            f"Memória: {settings.memory_profile} | "
            f"Precisão: {settings.compute_type} | "
            f"Beam: {settings.beam_size} | "
            f"Idioma: {settings.language}"
        )

    def _output_dir_for_input(self, input_path: Path) -> Path:
        return self._controller.output_dir_for_input(
            input_path, self.output_dir.get()
        )

    def _pick_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar áudio ou vídeo",
            filetypes=AUDIO_VIDEO_TYPES,
        )
        if path:
            self.input_path.set(path)
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

    def _show_progress_percent(self, percent: int, message: str) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = percent
        self.progress_text.set(message)
        self._refresh_progress_ui()

    def _reset_progress(self) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar["value"] = 0
        self.progress_text.set("")
        self._refresh_progress_ui()

    def _progress_elapsed(self) -> int:
        if self._progress_started_at is None:
            return 0
        return int(time.monotonic() - self._progress_started_at)

    def _progress_wait_suffix(self) -> str:
        return f" (aguarde, {self._progress_elapsed()}s)"

    def _classify_progress(self, ratio: float, message: str | None) -> str:
        """Fase estável para o rótulo (ignora detalhes voláteis do worker)."""
        if message:
            lower = message.lower()
            if message in ("loading", "transcribing", "diarizing", "saving"):
                return message
            if "arquivo " in message and "/" in message:
                return "batch"
            if "diariz" in lower:
                return "diarizing"
            if "salvando" in lower:
                return "saving"
            if "preparando" in lower:
                return "preparing"
            if "carregando" in lower or "modelo" in lower:
                return "loading"
        if ratio < 0:
            return "indeterminate"
        if ratio <= 0 and (not message or message == "loading"):
            return "loading"
        return "transcribing"

    def _progress_display_text(self, kind: str, percent: int, message: str | None) -> str:
        suffix = self._progress_wait_suffix()
        if kind == "batch" and message:
            base = message.strip()
            if "%" not in base and percent > 0:
                base = f"{base} — {percent}%"
            return base + suffix
        labels = {
            "preparing": f"Preparando arquivo… {percent}%",
            "loading": (
                f"Carregando modelo {self._progress_model_label} e transcrevendo"
            ),
            "transcribing": f"Transcrevendo… {percent}%",
            "diarizing": f"Diarizando falantes… {percent}%",
            "saving": f"Salvando arquivo… {percent}%",
            "indeterminate": message or "Processando…",
        }
        base = labels.get(kind, f"Transcrevendo… {percent}%")
        if kind == "indeterminate" and "(aguarde," in base:
            return base
        return base + suffix

    def _apply_progress(self, ratio: float, message: str | None) -> None:
        """Atualiza barra e texto de progresso na thread principal."""
        if ratio >= 0:
            self._progress_ratio = max(0.0, min(ratio, 1.0))
        if message is not None:
            self._progress_raw_message = message

        kind = self._classify_progress(self._progress_ratio, message)
        percent = int(self._progress_ratio * 100)
        elapsed = self._progress_elapsed()
        display = self._progress_display_text(kind, percent, message)

        if kind in ("loading", "indeterminate") and percent == 0 and self._progress_ratio == 0:
            if (
                elapsed == self._last_shown_elapsed
                and display == self.progress_text.get()
            ):
                return
            self._last_shown_elapsed = elapsed
            self._show_progress_indeterminate(display)
            return

        if (
            percent == self._last_shown_percent
            and elapsed == self._last_shown_elapsed
            and display == self.progress_text.get()
        ):
            return
        self._last_shown_percent = percent
        self._last_shown_elapsed = elapsed
        self._show_progress_percent(percent, display)

    def _flush_progress_queue(self) -> None:
        while True:
            try:
                self._progress_queue.get_nowait()
            except queue.Empty:
                break

    def _process_progress_item(self, item) -> None:
        if isinstance(item[0], str) and item[0] == "__callback__":
            _, job_id, callback, args = item
            if job_id == self._job_id:
                self.after(0, lambda c=callback, a=args: c(*a))
            return

        job_id, ratio, message = item
        if job_id != self._job_id:
            return
        self._apply_progress(ratio, message)

    def _schedule_on_main(self, callback, *args) -> None:
        """Agenda callback na thread principal (seguro a partir de worker)."""
        self._progress_queue.put(("__callback__", self._job_id, callback, args))

    def _report_progress(self, ratio: float, message: str | None) -> None:
        """Pode ser chamado da thread de trabalho; enfileira para a UI."""
        self._progress_queue.put((self._job_id, ratio, message))

    def _drain_progress_queue(self) -> None:
        while True:
            try:
                item = self._progress_queue.get_nowait()
            except queue.Empty:
                break
            self._process_progress_item(item)

    def _poll_ui_queue(self) -> None:
        self._drain_progress_queue()
        self.after(50, self._poll_ui_queue)

    def _start_progress_timer(self, model_size: str = "base") -> None:
        self._stop_progress_timer()
        self._progress_model_label = model_size
        self._progress_started_at = time.monotonic()
        self._progress_ratio = 0.0
        self._progress_raw_message = None
        self._last_shown_percent = -1
        self._last_shown_elapsed = -1
        self._schedule_progress_timer_tick()

    def _schedule_progress_timer_tick(self) -> None:
        if self._progress_started_at is None:
            return
        self._apply_progress(self._progress_ratio, self._progress_raw_message)
        self._progress_timer_after = self.after(1000, self._schedule_progress_timer_tick)

    def _stop_progress_timer(self) -> None:
        if self._progress_timer_after is not None:
            try:
                self.after_cancel(self._progress_timer_after)
            except tk.TclError:
                pass
            self._progress_timer_after = None
        self._progress_started_at = None

    def _is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def _cancel_transcription(self) -> None:
        if not self._cancel_event.is_set():
            self._cancel_event.set()
            self.cancel_btn.configure(state=tk.DISABLED)
            self._apply_progress(0.0, "Cancelando…")

    def _speaker_id_ready(self) -> bool:
        if not self.identify_speakers.get():
            return True
        from audiotranscriber.services.diarization_backend import (
            diarization_install_hint,
            is_diarization_available,
        )

        if is_diarization_available():
            return True
        messagebox.showwarning(
            "Identificar falantes",
            "Diarização indisponível.\n\n"
            f"{diarization_install_hint()}\n\n"
            "Desmarque a opção ou configure HF_TOKEN e tente de novo.",
        )
        return False

    def _begin_transcription_job(self) -> None:
        self._job_id += 1
        self._cancel_event.clear()
        self._stop_progress_timer()
        self._flush_progress_queue()
        self._log(f"job {self._job_id}: validação OK, preparando UI")
        self._set_busy(True)
        self.cancel_btn.configure(state=tk.NORMAL)
        self._log(f"job {self._job_id}: iniciando worker")

    def _set_files_inputs_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in (
            getattr(self, "input_entry", None),
            getattr(self, "output_entry", None),
            getattr(self, "output_name_entry", None),
            getattr(self, "batch_output_entry", None),
            self.batch_listbox,
            getattr(self, "identify_speakers_btn", None),
        ):
            if widget is not None:
                widget.configure(state=state)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.transcribe_btn.configure(state=state)
        self.cancel_btn.configure(state=tk.NORMAL if busy else tk.DISABLED)
        self.quality_combo.configure(state="disabled" if busy else "readonly")
        self._set_files_inputs_enabled(not busy)
        if busy:
            self._update_preset_fields_state(self._get_preset_key())
            for combo in self._preset_combos:
                combo.configure(state="disabled")
            self._language_combo.configure(state="disabled")
        else:
            self._stop_progress_timer()
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.quality_combo.configure(state="readonly")
            self._language_combo.configure(state="readonly")
            self._update_preset_fields_state(self._get_preset_key())
            if not self.progress_text.get().strip():
                self.status.set(f"Dispositivo: {self._controller.device}")

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
            self._reset_run_log()
            self._log("Botão Transcrever clicado")
            self._log("Modo: um arquivo")
            self._log("Abortado: nenhum arquivo de entrada selecionado")
            messagebox.showwarning("Atenção", "Selecione um arquivo de entrada.")
            return

        input_path = Path(input_file)
        if not input_path.is_file():
            self._reset_run_log(input_path.parent)
            self._log("Botão Transcrever clicado")
            self._log("Modo: um arquivo")
            self._log(f"Abortado: arquivo não encontrado: {input_file}")
            messagebox.showerror("Erro", "Arquivo de entrada não encontrado.")
            return

        output_path = self._output_dir_for_input(input_path)
        self._reset_run_log(output_path)
        self._log("Botão Transcrever clicado")
        self._log("Modo: um arquivo")
        if output_folder:
            self._log(f"Entrada: {input_path}")
            self._log(f"Saída: {output_path}")
        else:
            self._log(f"Entrada: {input_path}")
            self._log(f"Saída: {output_path} (pasta do arquivo de entrada)")

        if not self._speaker_id_ready():
            return

        try:
            settings = self._build_settings()
            identify = self.identify_speakers.get()
            self._log(
                f"Config: preset={settings.quality_preset}, "
                f"modelo={settings.model_size}, idioma={settings.language}, "
                f"falantes={identify}"
            )
            self._begin_transcription_job()
            self._apply_progress(0.0, "preparing")

            thread = threading.Thread(
                target=self._run_single_transcription,
                args=(
                    input_path,
                    output_path,
                    output_name,
                    settings,
                    self.include_timestamps.get(),
                    identify,
                ),
                daemon=True,
            )
            thread.start()
            self._log(f"job {self._job_id}: thread de transcrição iniciada")
        except Exception as exc:
            detail = f"{exc}\n\n{traceback.format_exc()}"
            self._log(f"ERRO ao iniciar transcrição:\n{detail}")
            self._set_busy(False)
            messagebox.showerror(
                "Erro ao iniciar",
                f"{exc}\n\nDetalhes em:\n{self._run_log_path()}",
            )

    def _start_batch_transcription(self) -> None:
        output_folder = self.output_dir.get().strip()

        if not self._batch_paths:
            self._reset_run_log()
            self._log("Botão Transcrever clicado")
            self._log("Modo: vários arquivos")
            self._log("Abortado: lista de lote vazia")
            messagebox.showwarning("Atenção", "Adicione pelo menos um arquivo à lista.")
            return

        paths = [Path(p) for p in self._batch_paths]
        missing = [p.name for p in paths if not p.is_file()]
        if missing:
            log_dir = paths[0].parent if paths else None
            self._reset_run_log(log_dir)
            self._log("Botão Transcrever clicado")
            self._log("Modo: vários arquivos")
            self._log(f"Abortado: arquivos ausentes: {', '.join(missing[:5])}")
            messagebox.showerror(
                "Erro",
                "Arquivos não encontrados:\n" + "\n".join(missing[:10]),
            )
            return

        use_input_folder = not output_folder
        log_dir = (
            Path(output_folder).resolve()
            if output_folder
            else paths[0].resolve().parent
        )
        self._reset_run_log(log_dir)
        self._log("Botão Transcrever clicado")
        self._log("Modo: vários arquivos")
        if output_folder:
            self._log(f"Lote: {len(paths)} arquivo(s) -> {output_folder}")
        else:
            self._log(
                f"Lote: {len(paths)} arquivo(s) -> pasta de cada arquivo de entrada"
            )

        if not self._speaker_id_ready():
            return

        settings = self._build_settings()
        identify = self.identify_speakers.get()
        self._log(f"Config lote: falantes={identify}")
        self._begin_transcription_job()
        self._apply_progress(
            0.0, f"Arquivo 0/{len(paths)} — preparando lote… 0%"
        )

        thread = threading.Thread(
            target=self._run_batch_transcription,
            args=(
                paths,
                Path(output_folder) if output_folder else None,
                use_input_folder,
                settings,
                self.include_timestamps.get(),
                identify,
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
        identify_speakers: bool,
    ) -> None:
        self._start_progress_timer(settings.model_size)

        def log_line(message: str) -> None:
            self._log(f"job {self._job_id}: {message}")

        try:
            output_file = self._controller.run_single(
                input_path,
                output_dir,
                output_name,
                settings,
                include_timestamps,
                identify_speakers,
                on_progress=self._report_progress,
                is_cancelled=self._is_cancelled,
                log=log_line,
            )
            self._schedule_on_main(self._on_single_success, output_file)
        except TranscriptionCancelled:
            self._schedule_on_main(self._on_cancelled)
        except Exception as exc:
            detail = f"{exc}\n\n{traceback.format_exc()}"
            self._schedule_on_main(self._on_error, detail)
        finally:
            self._stop_progress_timer()

    def _run_batch_transcription(
        self,
        paths: list[Path],
        output_dir: Path | None,
        use_input_folder: bool,
        settings: TranscriptionSettings,
        include_timestamps: bool,
        identify_speakers: bool,
    ) -> None:
        self._start_progress_timer(settings.model_size)

        def log_line(message: str) -> None:
            self._log(f"job {self._job_id}: {message}")

        try:
            saved, errors, cancelled = self._controller.run_batch(
                paths,
                output_dir,
                use_input_folder,
                settings,
                include_timestamps,
                identify_speakers,
                on_progress=self._report_progress,
                is_cancelled=self._is_cancelled,
                log=log_line,
            )
            summary_dir = (
                output_dir
                if output_dir is not None
                else (paths[0].resolve().parent if paths else Path("."))
            )
            if cancelled:
                self._schedule_on_main(
                    self._on_batch_cancelled, saved, errors, summary_dir
                )
            else:
                self._schedule_on_main(
                    self._on_batch_finished, saved, errors, summary_dir
                )
        except Exception as exc:
            detail = f"{exc}\n\n{traceback.format_exc()}"
            self._log(f"job {self._job_id}: batch error\n{detail}")
            self._schedule_on_main(self._on_error, detail)
        finally:
            self._stop_progress_timer()

    def _on_single_success(self, output_file: Path) -> None:
        self._set_busy(False)
        done_msg = "Concluído (100%)"
        self._show_progress_percent(100, done_msg)
        self.status.set(f"Salvo em: {output_file}")
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
        self._show_progress_percent(100, "Concluído (100%)")

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

    def _on_cancelled(self) -> None:
        self._set_busy(False)
        self.progress_bar["value"] = 0
        self.progress_text.set("Cancelado")
        self.status.set("Transcrição cancelada.")
        messagebox.showinfo("Cancelado", "A transcrição foi cancelada.")

    def _on_batch_cancelled(
        self,
        saved: list[Path],
        errors: list[str],
        output_dir: Path,
    ) -> None:
        self._set_busy(False)
        self.progress_bar["value"] = 0
        self.progress_text.set("Cancelado")
        ok_count = len(saved)
        if ok_count:
            self.status.set(
                f"Cancelado — {ok_count} arquivo(s) já salvo(s) em: {output_dir}"
            )
            messagebox.showinfo(
                "Cancelado",
                f"Lote interrompido.\n{ok_count} arquivo(s) já transcrito(s) em:\n{output_dir}",
            )
        else:
            self.status.set("Lote cancelado.")
            messagebox.showinfo("Cancelado", "O lote foi cancelado.")

    def _on_error(self, detail: str) -> None:
        self._set_busy(False)
        self.progress_text.set("Erro")
        log_path = self._run_log_path()
        summary = detail.splitlines()[0] if detail else "Erro desconhecido"
        self._log(f"ERRO na UI: {detail}")
        self.status.set(f"Erro: {summary}")
        messagebox.showerror(
            "Erro",
            f"{summary}\n\nDetalhes também em:\n{log_path}",
        )


def main() -> None:
    issues = run_startup_checks()
    if issues:
        body = format_issues(issues)
        if has_blocking_errors(issues):
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("AudioTranscriber — dependências", body)
            root.destroy()
            raise SystemExit(1)
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("AudioTranscriber — avisos", body)
        root.destroy()

    app = TranscriberApp()
    app.mainloop()


if __name__ == "__main__":
    main()
