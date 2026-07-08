import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os

import wav_cleaner


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Remove WAV Loop Points")
        self.root.geometry("650x450")
        self.root.resizable(False, False)

        self.folder = ""

        tk.Label(
            root,
            text="Remove Loop Points from WAV files",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        self.path_label = tk.Label(
            root,
            text="No folder selected",
            wraplength=620,
            fg="blue"
        )
        self.path_label.pack()

        tk.Button(
            root,
            text="Select Folder",
            width=20,
            command=self.select_folder
        ).pack(pady=10)

        self.start_button = tk.Button(
            root,
            text="Start",
            width=20,
            state=tk.DISABLED,
            command=self.start
        )
        self.start_button.pack()

        self.progress = tk.Label(root, text="")
        self.progress.pack(pady=10)

        self.log = tk.Text(
            root,
            width=80,
            height=18,
            state=tk.DISABLED
        )
        self.log.pack(padx=10, pady=5)

    def write_log(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def select_folder(self):
        folder = filedialog.askdirectory()

        if folder:
            self.folder = folder
            self.path_label.config(text=folder)
            self.start_button.config(state=tk.NORMAL)

    def start(self):
        self.start_button.config(state=tk.DISABLED)
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

        thread = threading.Thread(target=self.process)
        thread.daemon = True
        thread.start()

    def process(self):

        total = 0
        modified = 0

        def callback(message):
            self.root.after(0, lambda: self.write_log(message))

        for root_dir, _, files in os.walk(self.folder):

            for file in files:

                if not file.lower().endswith(".wav"):
                    continue

                total += 1

                path = os.path.join(root_dir, file)

                try:

                    changed = wav_cleaner.clean_wav(path)

                    if changed:
                        modified += 1
                        callback(f"✔ {file}")
                    else:
                        callback(f"• {file} (already clean)")

                except Exception as e:
                    callback(f"✖ {file}: {e}")

        self.root.after(
            0,
            lambda: self.finish(total, modified)
        )

    def finish(self, total, modified):

        self.progress.config(
            text=f"Done! Processed: {total}    Modified: {modified}"
        )

        self.start_button.config(state=tk.NORMAL)

        messagebox.showinfo(
            "Finished",
            f"Processed: {total}\nModified: {modified}"
        )


def main():

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
