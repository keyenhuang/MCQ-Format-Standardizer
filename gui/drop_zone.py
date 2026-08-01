from pathlib import Path
from typing import Callable, List

import customtkinter as ctk
from tkinterdnd2 import DND_FILES


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, on_files_dropped: Callable[[List[Path]], None], **kwargs):
        super().__init__(parent, height=140, border_width=2,
                         border_color=("#3B82F6", "#2563EB"),
                         fg_color=("#F8FAFC", "#1E293B"),
                         corner_radius=14, **kwargs)
        self.pack_propagate(False)
        self.on_files_dropped = on_files_dropped

        self.drop_label = ctk.CTkLabel(
            self,
            text="📂 Drag & Drop MCQ files here (.docx, .txt)\nor Click to Browse",
            font=("Segoe UI", 14, "bold"), text_color=("#2563EB", "#60A5FA"), cursor="hand2"
        )
        self.drop_label.pack(expand=True, fill="both")

        self.setup_dnd()

    def setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self._on_drag_leave)

    def _on_drag_enter(self, event):
        self.configure(border_color=("#10B981", "#059669"), fg_color=("#ECFDF5", "#064E3B"))

    def _on_drag_leave(self, event):
        self.configure(border_color=("#3B82F6", "#2563EB"), fg_color=("#F8FAFC", "#1E293B"))


    def handle_drop(self, event):
        from tkinter import messagebox
        try:
            if not event.data:
                return
            paths = self.tk.splitlist(event.data)
            valid = [Path(p) for p in paths if Path(p).suffix.lower() in ('.docx', '.txt')]
            if valid:
                self.on_files_dropped(valid)
            else:
                messagebox.showwarning("Warning", "Please drop .docx or .txt files.")
        except (ValueError, OSError):
            pass
        finally:
            self._on_drag_leave(None)
