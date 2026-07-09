import os
import threading

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

import wav_cleaner


# ---------------------------------------------------------------------------
# Позволяет совместить customtkinter (красивый вид) и tkinterdnd2 (drag&drop)
# в одном окне — стандартный способ подружить эти две библиотеки.
# ---------------------------------------------------------------------------
class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLOR_OK = "#4ADE80"
COLOR_SKIP = "#9CA3AF"
COLOR_ERR = "#F87171"
COLOR_MUTED = "#9CA3AF"
COLOR_ACCENT = "#3B82F6"


class App:
    def __init__(self, root: DnDCTk):
        self.root = root
        self.root.title("LoopPointCleaner")
        self.root.geometry("720x640")
        self.root.minsize(600, 520)

        self.selected_paths = []

        # ---------- Header ----------
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 12))

        ctk.CTkLabel(
            header,
            text="loop point cleaner",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Removing loop points from wav files",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # ---------- Drop zone ----------
        self.drop_frame = ctk.CTkFrame(
            root,
            corner_radius=14,
            border_width=2,
            border_color="#3A3A3A",
            fg_color="#212121",
            height=120,
        )
        self.drop_frame.pack(fill="x", padx=24, pady=8)
        self.drop_frame.pack_propagate(False)

        self.drop_label = ctk.CTkLabel(
            self.drop_frame,
            text="Перетащите папку, файл(ы) сюда\nили выберите вручную",
            font=ctk.CTkFont(size=14),
            text_color=COLOR_MUTED,
            justify="center",
        )
        self.drop_label.pack(expand=True)

        # Drag & drop на всю зону и на подпись
        for widget in (self.drop_frame, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.on_drop)

        # ---------- Path + select ----------
        path_row = ctk.CTkFrame(root, fg_color="transparent")
        path_row.pack(fill="x", padx=24, pady=(4, 8))

        self.path_label = ctk.CTkLabel(
            path_row,
            text="Ничего не выбрано",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_MUTED,
            anchor="w",
        )
        self.path_label.pack(side="left", fill="x", expand=True)

        buttons_wrap = ctk.CTkFrame(path_row, fg_color="transparent")
        buttons_wrap.pack(side="right")

        ctk.CTkButton(
            buttons_wrap,
            text="Выбрать файлы",
            width=130,
            fg_color="transparent",
            border_width=1,
            border_color="#3A3A3A",
            command=self.select_files,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            buttons_wrap,
            text="Выбрать папку",
            width=130,
            command=self.select_folder,
        ).pack(side="left")

        # ---------- Actions ----------
        actions = ctk.CTkFrame(root, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(8, 4))

        self.start_button = ctk.CTkButton(
            actions,
            text="▶  Запустить обработку",
            state="disabled",
            fg_color=COLOR_ACCENT,
            command=self.start,
        )
        self.start_button.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.clear_button = ctk.CTkButton(
            actions,
            text="Очистить лог",
            width=120,
            fg_color="transparent",
            border_width=1,
            border_color="#3A3A3A",
            command=self.clear_log,
        )
        self.clear_button.pack(side="left")

        # ---------- Progress ----------
        progress_wrap = ctk.CTkFrame(root, fg_color="transparent")
        progress_wrap.pack(fill="x", padx=24, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(progress_wrap)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 10))

        self.progress_pct = ctk.CTkLabel(progress_wrap, text="0%", width=40)
        self.progress_pct.pack(side="left")

        # ---------- Stats badges ----------
        stats_row = ctk.CTkFrame(root, fg_color="transparent")
        stats_row.pack(fill="x", padx=24, pady=(4, 8))

        self.stat_total = self._make_stat(stats_row, "Обработано", COLOR_MUTED)
        self.stat_modified = self._make_stat(stats_row, "Изменено", COLOR_OK)
        self.stat_errors = self._make_stat(stats_row, "Ошибок", COLOR_ERR)

        # ---------- Log ----------
        self.log = ctk.CTkTextbox(
            root,
            font=ctk.CTkFont(family="Consolas", size=12),
            corner_radius=10,
            fg_color="#1A1A1A",
        )
        self.log.pack(fill="both", expand=True, padx=24, pady=(4, 8))
        self.log.configure(state="disabled")

        self.log.tag_config("ok", foreground=COLOR_OK)
        self.log.tag_config("skip", foreground=COLOR_SKIP)
        self.log.tag_config("err", foreground=COLOR_ERR)

        # ---------- Status bar ----------
        self.status_bar = ctk.CTkLabel(
            root,
            text="Готово к работе",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_MUTED,
            anchor="w",
        )
        self.status_bar.pack(fill="x", padx=24, pady=(0, 12))

    # -----------------------------------------------------------------
    def _make_stat(self, parent, label, color):
        box = ctk.CTkFrame(parent, fg_color="#212121", corner_radius=10)
        box.pack(side="left", fill="x", expand=True, padx=(0, 8))

        value = ctk.CTkLabel(
            box, text="0", font=ctk.CTkFont(size=18, weight="bold"), text_color=color
        )
        value.pack(pady=(10, 0))

        ctk.CTkLabel(
            box, text=label, font=ctk.CTkFont(size=11), text_color=COLOR_MUTED
        ).pack(pady=(0, 10))

        return value

    # -----------------------------------------------------------------
    def on_drop(self, event):
        # tkinterdnd2 может прислать несколько путей за раз; splitlist корректно
        # разбирает их, даже если в путях есть пробелы (обёрнуты в {})
        raw_paths = self.root.tk.splitlist(event.data)

        valid = [
            p for p in raw_paths
            if os.path.isdir(p) or p.lower().endswith(".wav")
        ]

        if not valid:
            self.status_bar.configure(
                text="Перетащите папку или .wav файлы"
            )
            return

        self.set_paths(valid)

    def select_folder(self):
        folder = ctk.filedialog.askdirectory()
        if folder:
            self.set_paths([folder])

    def select_files(self):
        files = ctk.filedialog.askopenfilenames(
            title="Выберите WAV-файлы",
            filetypes=[("WAV files", "*.wav"), ("Все файлы", "*.*")],
        )
        if files:
            self.set_paths(list(files))

    def set_paths(self, paths):
        self.selected_paths = paths

        if len(paths) == 1:
            single = paths[0]
            is_folder = os.path.isdir(single)
            self.path_label.configure(text=single, text_color="white")
            icon = "📁" if is_folder else "🎵"
            self.drop_label.configure(text=f"{icon} {os.path.basename(single) or single}")
        else:
            folders = sum(1 for p in paths if os.path.isdir(p))
            files = len(paths) - folders
            summary = []
            if folders:
                summary.append(f"{folders} папк(и/а)")
            if files:
                summary.append(f"{files} файл(ов)")
            text = " и ".join(summary)
            self.path_label.configure(text=f"Выбрано: {text}", text_color="white")
            self.drop_label.configure(text=f"🎵 Выбрано объектов: {len(paths)}")

        self.start_button.configure(state="normal")
        self.status_bar.configure(text="Готово к запуску")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def write_log(self, text, tag):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_stats(self, total, modified, errors):
        self.stat_total.configure(text=str(total))
        self.stat_modified.configure(text=str(modified))
        self.stat_errors.configure(text=str(errors))

    # -----------------------------------------------------------------
    def start(self):
        self.start_button.configure(state="disabled")
        self.clear_log()
        self.progress_bar.set(0)
        self.progress_pct.configure(text="0%")
        self.set_stats(0, 0, 0)
        self.status_bar.configure(text="Поиск WAV-файлов…")

        thread = threading.Thread(target=self.process)
        thread.daemon = True
        thread.start()

    def process(self):
        wav_files = []

        for path in self.selected_paths:
            if os.path.isdir(path):
                for root_dir, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith(".wav"):
                            wav_files.append(os.path.join(root_dir, file))
            elif path.lower().endswith(".wav") and os.path.isfile(path):
                wav_files.append(path)

        # на случай, если один и тот же файл попал и напрямую, и через папку
        wav_files = list(dict.fromkeys(wav_files))

        total_files = len(wav_files)
        processed = 0
        modified = 0
        errors = 0

        if total_files == 0:
            self.root.after(0, lambda: self.finish(0, 0, 0))
            return

        for path in wav_files:
            file = os.path.basename(path)

            try:
                changed = wav_cleaner.clean_wav(path)
                if changed:
                    modified += 1
                    tag, prefix = "ok", "✔"
                else:
                    tag, prefix = "skip", "•"
            except Exception as e:
                errors += 1
                tag, prefix = "err", "✖"
                file = f"{file}: {e}"

            processed += 1
            fraction = processed / total_files

            self.root.after(
                0,
                lambda f=file, t=tag, p=prefix, fr=fraction,
                pr=processed, m=modified, er=errors: self.update_progress(
                    f, t, p, fr, pr, m, er
                ),
            )

        self.root.after(0, lambda: self.finish(processed, modified, errors))

    def update_progress(self, file, tag, prefix, fraction, processed, modified, errors):
        self.write_log(f"{prefix} {file}", tag)
        self.progress_bar.set(fraction)
        self.progress_pct.configure(text=f"{int(fraction * 100)}%")
        self.set_stats(processed, modified, errors)
        self.status_bar.configure(text=f"Обработка… {processed} файл(ов)")

    def finish(self, total, modified, errors):
        self.start_button.configure(state="normal")
        self.progress_bar.set(1 if total else 0)
        self.progress_pct.configure(text="100%" if total else "0%")

        if total == 0:
            self.status_bar.configure(text="WAV-файлы не найдены")
            self.write_log("В выбранных папке/файлах нет .wav файлов", "skip")
            return

        self.status_bar.configure(
            text=f"Готово. Обработано {total}, изменено {modified}, ошибок {errors}"
        )


def main():
    root = DnDCTk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
