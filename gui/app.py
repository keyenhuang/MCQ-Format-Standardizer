from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

from parser import parse_docx, parse_txt, renumber_docx_inplace, renumber_txt_inplace, count_math_formulas
from formatter import build_output_document
from gui.chat_sidebar import ChatSidebar
from gui.drop_zone import DropZone
from gui.file_manager import FileManager
from gui.converter import run_conversion, ConversionResult
from logger import get_logger

logger = get_logger()


class TkinterDnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class MCQFormatStandardizerApp(TkinterDnDCTk):
    def __init__(self):
        super().__init__()
        self.title("MCQ Format Standardizer")
        self.geometry("960x650")
        self.minsize(800, 550)
        self.resizable(True, True)

        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#F1F5F9")

        self.file_manager = FileManager()
        self.setup_ui()
        self.sidebar = ChatSidebar(self.right_frame, self)

    def setup_ui(self):
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=20)

        self.right_frame = ctk.CTkFrame(
            self, width=380, corner_radius=15,
            fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0"
        )
        self.right_frame.pack(side="right", fill="both", expand=False, padx=(10, 20), pady=20)
        self.right_frame.pack_propagate(False)

        self._build_header()
        self.drop_zone = DropZone(self.left_frame, self.on_files_dropped)
        self.drop_zone.pack(fill="x", pady=10, padx=10)
        self._build_file_info()
        self._build_mode_selector()
        self._build_action_buttons()
        self._build_progress()
        self._build_status()

    def on_files_dropped(self, paths):
        new_files = self.file_manager.add_files(paths)
        if not new_files:
            return
        self._update_file_info()
        names = ", ".join(f"{p.name}" for p in paths)
        mode_str = "Standardize Format" if self.mode_var.get() == "standard" else "Only Renumber"
        msg = f"Added to conversion queue:\n- {names}\n\n(Ready to process in {mode_str} mode)"
        actions = [
            {"text": "Convert Now", "command": self.start_conversion},
            {"text": "Clear", "command": lambda: self.clear_selection(notify=True)}
        ]
        self.sidebar.add_chat_message("Copilot", msg, actions=actions)

    def _build_header(self):
        header = ctk.CTkLabel(
            self.left_frame, text="MCQ Format Standardizer",
            font=("Segoe UI", 26, "bold"), text_color="#1E293B"
        )
        header.pack(pady=(10, 5))
        subheader = ctk.CTkLabel(
            self.left_frame, text="Advanced Batch MCQ Processing (Supports formulas)",
            font=("Segoe UI", 13), text_color="#64748B"
        )
        subheader.pack(pady=(0, 10))

    def _build_file_info(self):
        self.file_info_var = ctk.StringVar(value="No files selected")
        self.file_info_label = ctk.CTkLabel(
            self.left_frame, textvariable=self.file_info_var,
            font=("Segoe UI", 11, "italic"), wraplength=480
        )
        self.file_info_label.pack(pady=5)
        self.file_info_label.bind("<Button-1>", lambda e: self.choose_files())

    def _update_file_info(self):
        self.file_info_var.set(self.file_manager.summary)
        has_files = self.file_manager.count > 0
        self.drop_zone.configure(border_color="green" if has_files else "#3B82F6")
        self.convert_btn.configure(state="normal" if has_files else "disabled")
        self.status_var.set(
            f"Ready to convert {self.file_manager.count} files." if has_files else "Ready"
        )

    def _build_mode_selector(self):
        self.mode_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.mode_frame.pack(pady=5)
        self.mode_var = ctk.StringVar(value="standard")

        self.radio_standard = ctk.CTkRadioButton(
            self.mode_frame, text="Standardize Format",
            variable=self.mode_var, value="standard",
            text_color="#1E293B", fg_color="#2563EB", hover_color="#3B82F6"
        )
        self.radio_standard.pack(side="left", padx=15)

        self.radio_renumber = ctk.CTkRadioButton(
            self.mode_frame, text="Only Renumber",
            variable=self.mode_var, value="renumber",
            text_color="#1E293B", fg_color="#2563EB", hover_color="#3B82F6"
        )
        self.radio_renumber.pack(side="left", padx=15)

    def _build_action_buttons(self):
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(pady=15)

        self.convert_btn = ctk.CTkButton(
            self.button_frame, text="Convert All",
            command=self.start_conversion, state="disabled",
            fg_color="#F97316", hover_color="#EA580C",
            text_color="white", font=("Segoe UI", 15, "bold"), corner_radius=8
        )
        self.convert_btn.pack(side="left", padx=10)

        self.clear_btn = ctk.CTkButton(
            self.button_frame, text="Clear List",
            fg_color="transparent", hover_color="#F1F5F9",
            border_width=1, border_color="#CBD5E1",
            text_color="#64748B", command=lambda: self.clear_selection(),
            corner_radius=8
        )
        self.clear_btn.pack(side="left", padx=10)

    def _build_progress(self):
        self.progress_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame, height=12, corner_radius=6, progress_color="#10B981"
        )
        self.progress_bar.pack(side="left", fill="x", expand=True)
        self.progress_percent_var = ctk.StringVar(value="0%")
        self.progress_percent_label = ctk.CTkLabel(
            self.progress_frame, textvariable=self.progress_percent_var,
            font=("Segoe UI", 12, "bold"), text_color="#10B981", width=40
        )
        self.progress_percent_label.pack(side="right", padx=(8, 0))

    def _build_status(self):
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            self.left_frame, textvariable=self.status_var,
            font=("Segoe UI", 13, "bold"), text_color="#2563EB"
        )
        self.status_label.pack(side="bottom", pady=10)

    def choose_files(self):
        paths = filedialog.askopenfilenames(
            title="Select MCQ Input Files",
            filetypes=[
                ("Supported Files", "*.docx *.txt"),
                ("Word Documents", "*.docx"),
                ("Text Files", "*.txt")
            ]
        )
        if paths:
            self.on_files_dropped([Path(p) for p in paths])

    def clear_selection(self, notify=True):
        self.file_manager.clear()
        self._update_file_info()
        self.progress_frame.pack_forget()
        if notify:
            self.sidebar.add_chat_message("Copilot", "File queue cleared.")

    def start_conversion(self):
        if self.file_manager.count == 0:
            return

        files = self.file_manager.input_files
        if len(files) == 1:
            output_path = filedialog.asksaveasfilename(
                title="Save Converted File",
                defaultextension=".docx",
                initialdir=str(files[0].parent),
                initialfile=files[0].stem + "_standardized.docx",
                filetypes=[("Word Document", "*.docx")]
            )
            if not output_path:
                return
            targets = [(files[0], Path(output_path))]
        else:
            targets = [(f, f.with_name(f.stem + "_standardized.docx")) for f in files]

        self.status_var.set("Converting...")
        self.convert_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.progress_frame.pack(fill="x", padx=10, pady=10, before=self.status_label)
        self.progress_bar.set(0)
        self.progress_percent_var.set("0%")

        mode = self.mode_var.get()
        mode_str = "Standardize Format" if mode == "standard" else "Only Renumber"
        file_list = ", ".join(f"{f.name}" for f, _ in targets)
        self.sidebar.add_chat_message(
            "Copilot", f"Starting conversion for:\n- {file_list}\n\n(Mode: {mode_str})"
        )

        run_conversion(
            targets, mode,
            on_progress=self._on_conversion_progress,
            on_complete=lambda results: self.after(0, lambda: self._on_conversion_complete(results))
        )

    def _on_conversion_progress(self, current, total):
        pct = int((current / total) * 100)
        self.after(0, lambda: (self.status_var.set(f"Processing ({current}/{total})"),
                               self.progress_bar.set(current / total),
                               self.progress_percent_var.set(f"{pct}%")))

    def _on_conversion_complete(self, results):
        self.progress_bar.set(1.0)
        self.progress_percent_var.set("100%")
        success_count = sum(1 for r in results if r.status == "success")
        failed = [r for r in results if r.status == "error"]

        if failed:
            err_lines = [f"{r.filename}: {r.error_msg}" for r in failed[:5]]
            if len(failed) > 5:
                err_lines.append(f"... and {len(failed)-5} more.")
            messagebox.showerror("Failed", "\n".join(err_lines))

        self.status_var.set(f"Done! {success_count}/{len(results)} files converted.")
        messagebox.showinfo("Success", f"Successfully converted {success_count} of {len(results)} files.")

        lines = [f"Conversion Completed! Processed {success_count} of {len(results)} file(s).\n"]
        for r in results:
            if r.status == "success":
                parts = [f"- {r.filename}: Completed"]
                if r.math_count:
                    parts.append(f"({r.math_count} math formulas preserved)")
                if r.warnings:
                    parts.append("(with format warnings)")
                lines.append(" ".join(parts))
            else:
                lines.append(f"- {r.filename}: Failed. Reason: {r.error_msg}")
        self.sidebar.add_chat_message("Copilot", "\n".join(lines))

        self.file_manager.clear()
        self._update_file_info()
        self.clear_btn.configure(state="normal")
        self.progress_frame.pack_forget()
