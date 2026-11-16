from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
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

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=("#F1F5F9", "#0F172A"))

        self.file_manager = FileManager()
        self.setup_ui()
        self.sidebar = ChatSidebar(self.right_frame, self)

    def setup_ui(self):
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=20)

        self.right_frame = ctk.CTkFrame(
            self, width=380, corner_radius=16,
            fg_color=("#FFFFFF", "#1E293B"), border_width=1, border_color=("#E2E8F0", "#334155")
        )
        self.right_frame.pack(side="right", fill="both", expand=False, padx=(10, 20), pady=20)
        self.right_frame.pack_propagate(False)

        self._build_header()
        self.drop_zone = DropZone(self.left_frame, self.on_files_dropped, on_click=self.choose_files)
        self.drop_zone.pack(fill="x", pady=12, padx=5)
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
        names = ", ".join(f"{p.name}" for p in new_files)
        mode_str = self.seg_button.get()
        msg = f"Added to conversion queue:\n- {names}\n\n(Ready to process in {mode_str} mode)"
        actions = [
            {"text": "Convert Now", "command": self.start_conversion},
            {"text": "Clear", "command": lambda: self.clear_selection(notify=True)}
        ]
        self.sidebar.add_chat_message("Copilot", msg, actions=actions)

    def _build_header(self):
        header_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(5, 10))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        header = ctk.CTkLabel(
            title_box, text="MCQ Format Standardizer",
            font=("Segoe UI", 24, "bold"), text_color=("#1E293B", "#F8FAFC")
        )
        header.pack(anchor="w")
        subheader = ctk.CTkLabel(
            title_box, text="Batch MCQ Standardizing Engine (Supports OpenXML Math Formulas)",
            font=("Segoe UI", 12), text_color=("#64748B", "#94A3B8")
        )
        subheader.pack(anchor="w")

        theme_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        theme_box.pack(side="right", anchor="e")

        self.theme_menu = ctk.CTkOptionMenu(
            theme_box, values=["System", "Light", "Dark"],
            width=90, height=28, font=("Segoe UI", 11),
            command=lambda mode: ctk.set_appearance_mode(mode)
        )
        self.theme_menu.pack()

    def _build_file_info(self):
        self.file_info_var = ctk.StringVar(value="Input Queue: No files loaded")
        self.file_info_label = ctk.CTkLabel(
            self.left_frame, textvariable=self.file_info_var,
            font=("Segoe UI", 12, "italic"), text_color=("#475569", "#CBD5E1"),
            wraplength=480
        )
        self.file_info_label.pack(pady=6)
        self.file_info_label.bind("<Button-1>", lambda _e: self.choose_files())

    def _update_file_info(self):
        summary = self.file_manager.summary
        if summary == "No files selected":
            self.file_info_var.set("Input Queue: No files loaded")
        else:
            self.file_info_var.set(f"Input Queue: {summary}")

        has_files = self.file_manager.count > 0
        self.drop_zone.configure(border_color=("#10B981", "#059669") if has_files else ("#3B82F6", "#2563EB"))
        self.convert_btn.configure(state="normal" if has_files else "disabled")
        self.status_var.set(
            f"Ready to convert {self.file_manager.count} input file(s)." if has_files else "Ready"
        )

    def set_mode(self, mode: str):
        is_renumber = (mode == "renumber")
        self.mode_var.set("renumber" if is_renumber else "standard")
        self.seg_button.set("Renumber Only" if is_renumber else "Full Standardization")
        menu_state = "disabled" if is_renumber else "normal"
        self.format_menu.configure(state=menu_state)
        self.pos_menu.configure(state=menu_state)

    def _build_mode_selector(self):
        self.mode_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.mode_frame.pack(pady=8)

        self.mode_var = ctk.StringVar(value="standard")

        def _on_segmented_change(value):
            self.set_mode("renumber" if "Renumber" in value else "standard")

        self.seg_button = ctk.CTkSegmentedButton(
            self.mode_frame,
            values=["Full Standardization", "Renumber Only"],
            command=_on_segmented_change,
            selected_color=("#2563EB", "#1D4ED8"),
            selected_hover_color=("#1D4ED8", "#1E40AF"),
            unselected_color=("#CBD5E1", "#334155"),
            unselected_hover_color=("#94A3B8", "#475569"),
            text_color=("#0F172A", "#F8FAFC"),
            font=("Segoe UI", 13, "bold"), corner_radius=10
        )
        self.seg_button.set("Full Standardization")
        self.seg_button.pack(padx=10, pady=(5, 8))

        options_row = ctk.CTkFrame(self.mode_frame, fg_color="transparent")
        options_row.pack(fill="x", pady=2)

        ctk.CTkLabel(options_row, text="Output Format:", font=("Segoe UI", 11, "bold"), text_color=("#475569", "#CBD5E1")).pack(side="left", padx=(5, 2))
        self.export_format_var = ctk.StringVar(value="Word Doc (.docx)")
        self.format_menu = ctk.CTkOptionMenu(
            options_row, variable=self.export_format_var,
            values=["Word Doc (.docx)", "Moodle GIFT (.gift)", "JSON Data (.json)"],
            width=130, height=26, font=("Segoe UI", 11)
        )
        self.format_menu.pack(side="left", padx=(0, 15))

        ctk.CTkLabel(options_row, text="Answer Location:", font=("Segoe UI", 11, "bold"), text_color=("#475569", "#CBD5E1")).pack(side="left", padx=(5, 2))
        self.answer_pos_var = ctk.StringVar(value="Below Each Question")
        self.pos_menu = ctk.CTkOptionMenu(
            options_row, variable=self.answer_pos_var,
            values=["Below Each Question", "Separate Section at End"],
            width=160, height=26, font=("Segoe UI", 11)
        )
        self.pos_menu.pack(side="left")

    def _build_action_buttons(self):
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(pady=15)

        self.convert_btn = ctk.CTkButton(
            self.button_frame, text="Start Conversion",
            command=self.start_conversion, state="disabled",
            fg_color=("#F97316", "#EA580C"), hover_color=("#EA580C", "#C2410C"),
            text_color_disabled=("#64748B", "#94A3B8"),
            text_color="white", font=("Segoe UI", 15, "bold"), corner_radius=8
        )
        self.convert_btn.pack(side="left", padx=10)

        self.clear_btn = ctk.CTkButton(
            self.button_frame, text="Clear Queue",
            fg_color=("#E2E8F0", "#1E293B"), hover_color=("#CBD5E1", "#334155"),
            border_width=1, border_color=("#94A3B8", "#475569"),
            text_color=("#0F172A", "#F8FAFC"), font=("Segoe UI", 13, "bold"),
            command=lambda: self.clear_selection(),
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

    def _resolve_export_options(self):
        fmt_str = self.export_format_var.get()
        if "JSON" in fmt_str:
            return "json", ".json", [("JSON File", "*.json")]
        if "GIFT" in fmt_str:
            return "gift", ".gift", [("Moodle GIFT Text", "*.gift")]
        return "docx", ".docx", [("Word Document", "*.docx")]

    def _build_targets(self, files, mode, def_ext):
        if len(files) == 1:
            inp = files[0]
            if mode == "renumber":
                save_ext = inp.suffix.lower()
                ftypes = [("Word Document", "*.docx")] if save_ext == ".docx" else [("Text File", "*.txt")]
                default_name = f"{inp.stem}_renumbered{save_ext}"
            else:
                save_ext = def_ext
                _, _, ftypes = self._resolve_export_options()
                default_name = f"{inp.stem}_standardized{save_ext}"

            output_path = filedialog.asksaveasfilename(
                title="Save Converted File",
                defaultextension=save_ext,
                initialdir=str(inp.parent),
                initialfile=default_name,
                filetypes=ftypes
            )
            if not output_path:
                return None
            return [(inp, Path(output_path))]

        if mode == "renumber":
            return [(f, f.with_name(f"{f.stem}_renumbered{f.suffix}")) for f in files]
        return [(f, f.with_name(f"{f.stem}_standardized{def_ext}")) for f in files]

    def start_conversion(self):
        if self.file_manager.count == 0:
            return

        mode = self.mode_var.get()
        fmt_ext, def_ext, _ = self._resolve_export_options()
        answers_at_bottom = ("Separate Section" in self.answer_pos_var.get() or "End" in self.answer_pos_var.get())

        targets = self._build_targets(self.file_manager.input_files, mode, def_ext)
        if not targets:
            return

        self.status_var.set("Converting...")
        self.convert_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.progress_frame.pack(fill="x", padx=10, pady=10, before=self.status_label)
        self.progress_bar.set(0)
        self.progress_percent_var.set("0%")

        mode_str = "Standardize Format" if mode == "standard" else "Only Renumber"
        file_list = ", ".join(f"{f.name}" for f, _ in targets)
        fmt_display = "IN-PLACE" if mode == "renumber" else fmt_ext.upper()
        self.sidebar.add_chat_message(
            "Copilot", f"Starting conversion for:\n- {file_list}\n\n(Mode: {mode_str}, Format: {fmt_display})"
        )

        run_conversion(
            targets, mode,
            on_progress=self._on_conversion_progress,
            on_complete=lambda results: self.after(0, lambda r=results: self._on_conversion_complete(r)),
            export_format=fmt_ext,
            answers_at_bottom=answers_at_bottom
        )

    def _on_conversion_progress(self, current, total):
        ratio = (current / total) if total else 0
        pct = int(ratio * 100)
        self.after(0, lambda: (
            self.status_var.set(f"Processing ({current}/{total})"),
            self.progress_bar.set(ratio),
            self.progress_percent_var.set(f"{pct}%")
        ))

    def _on_conversion_complete(self, results):
        self.progress_bar.set(1.0)
        self.progress_percent_var.set("100%")
        success_count = sum(1 for r in results if r.status == "success")
        failed = [r for r in results if r.status == "error"]

        if failed:
            err_lines = [f"{r.filename}: {r.error_msg}" for r in failed[:5]]
            if len(failed) > 5:
                err_lines.append(f"... and {len(failed) - 5} more.")
            messagebox.showerror("Failed", "\n".join(err_lines))

        self.status_var.set(f"Done! {success_count}/{len(results)} files converted.")
        if success_count > 0:
            messagebox.showinfo("Success", f"Successfully converted {success_count} of {len(results)} files.")

        lines = [f"Conversion Completed! Processed {success_count} of {len(results)} file(s).\n"]
        for r in results:
            if r.status == "success":
                parts = [f"- {r.filename}: Completed"]
                if r.math_count:
                    parts.append(f"({r.math_count} math formulas preserved)")
                if r.warnings:
                    parts.append(f"({len(r.warnings)} format warning(s))")
                lines.append(" ".join(parts))
            else:
                lines.append(f"- {r.filename}: Failed. Reason: {r.error_msg}")
        self.sidebar.add_chat_message("Copilot", "\n".join(lines))

        if not failed:
            self.file_manager.clear()
        self._update_file_info()
        self.clear_btn.configure(state="normal")
        self.progress_frame.pack_forget()

