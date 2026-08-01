from pathlib import Path
from typing import Callable, List

import customtkinter as ctk
from tkinterdnd2 import DND_FILES


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, on_files_dropped: Callable[[List[Path]], None], **kwargs):
        super().__init__(parent, height=120, border_width=2,
                         border_color="#3B82F6", fg_color="#F8FAFC",
                         corner_radius=12, **kwargs)
        self.pack_propagate(False)
        self.on_files_dropped = on_files_dropped

        self.drop_label = ctk.CTkLabel(
            self,
            text="Drag and Drop files here\nor\nClick to Browse",
            font=("Segoe UI", 15), text_color="#3B82F6", cursor="hand2"
        )
        self.drop_label.pack(expand=True, fill="both")

        self.setup_dnd()

    def setup_dnd(self):
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)
        self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self._on_drag_leave)

    def _on_drag_enter(self, event):
        self.configure(border_color="#10B981", fg_color="#ECFDF5")

    def _on_drag_leave(self, event):
        self.configure(border_color="#3B82F6", fg_color="#F8FAFC")

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
