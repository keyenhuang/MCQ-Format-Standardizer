import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

from parser import (
    parse_docx, parse_txt, 
    renumber_docx_inplace, renumber_txt_inplace, 
    count_math_formulas, diagnose_error
)
from formatter import build_output_document
from gui.chat_sidebar import ChatSidebar

class TkinterDnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class MCQConverterApp(TkinterDnDCTk):
    def __init__(self):
        super().__init__()

        self.title("MCQ Batch Converter Pro")
        self.geometry("960x650")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#F1F5F9")

        self.input_files: List[Path] = []
        self.setup_ui()
        self.setup_dnd()

    def setup_ui(self):
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=20)
        
        self.right_frame = ctk.CTkFrame(self, width=380, corner_radius=15, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        self.right_frame.pack(side="right", fill="both", expand=False, padx=(10, 20), pady=20)
        self.right_frame.pack_propagate(False)

        self.header = ctk.CTkLabel(self.left_frame, text="MCQ Converter", font=("Segoe UI", 26, "bold"), text_color="#1E293B")
        self.header.pack(pady=(10, 5))

        self.subheader = ctk.CTkLabel(self.left_frame, text="Advanced Batch Processing (Supports formulas)", font=("Segoe UI", 13), text_color="#64748B")
        self.subheader.pack(pady=(0, 10))

        self.drop_frame = ctk.CTkFrame(self.left_frame, width=500, height=180, border_width=2, border_color="#3B82F6", fg_color="#F8FAFC", corner_radius=12)
        self.drop_frame.pack_propagate(False)
        self.drop_frame.pack(pady=10, padx=10)

        self.drop_label = ctk.CTkLabel(self.drop_frame, text="Drag and Drop files here\nor\nClick to Browse", 
                                      font=("Segoe UI", 15), text_color="#3B82F6", cursor="hand2")
        self.drop_label.pack(expand=True, fill="both")
        self.drop_label.bind("<Button-1>", lambda e: self.choose_files())

        self.file_info_var = ctk.StringVar(value="No files selected")
        self.file_info_label = ctk.CTkLabel(self.left_frame, textvariable=self.file_info_var, font=("Segoe UI", 11, "italic"), wraplength=480)
        self.file_info_label.pack(pady=5)

        self.mode_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.mode_frame.pack(pady=5)
        
        self.mode_var = ctk.StringVar(value="standard")
        
        self.radio_standard = ctk.CTkRadioButton(
            self.mode_frame, 
            text="Standardize Format", 
            variable=self.mode_var, 
            value="standard",
            text_color="#1E293B",
            fg_color="#2563EB",
            hover_color="#3B82F6"
        )
        self.radio_standard.pack(side="left", padx=15)
        
        self.radio_renumber = ctk.CTkRadioButton(
            self.mode_frame, 
            text="Only Renumber", 
            variable=self.mode_var, 
            value="renumber",
            text_color="#1E293B",
            fg_color="#2563EB",
            hover_color="#3B82F6"
        )
        self.radio_renumber.pack(side="left", padx=15)

        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(pady=15)

        self.convert_btn = ctk.CTkButton(self.button_frame, text="Convert All", command=self.start_conversion, state="disabled", 
                                         fg_color="#F97316", hover_color="#EA580C", text_color="white", font=("Segoe UI", 15, "bold"), corner_radius=8)
        self.convert_btn.pack(side="left", padx=10)

        self.clear_btn = ctk.CTkButton(self.button_frame, text="Clear List", fg_color="transparent", hover_color="#F1F5F9", 
                                       border_width=1, border_color="#CBD5E1", text_color="#64748B", command=self.clear_selection, corner_radius=8)
        self.clear_btn.pack(side="left", padx=10)

        self.progress_bar = ctk.CTkProgressBar(self.left_frame, width=400, height=12, corner_radius=6, progress_color="#10B981")
        self.progress_bar.set(0)
        
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(self.left_frame, textvariable=self.status_var, font=("Segoe UI", 13, "bold"), text_color="#2563EB")
        self.status_label.pack(side="bottom", pady=10)

        self.sidebar = ChatSidebar(self.right_frame, self)

    def setup_dnd(self):
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.drop_frame.dnd_bind('<<DragEnter>>', self.handle_drag_enter)
        self.drop_frame.dnd_bind('<<DragLeave>>', self.handle_drag_leave)

    def handle_drag_enter(self, event):
        self.drop_frame.configure(border_color="#10B981", fg_color="#ECFDF5")

    def handle_drag_leave(self, event):
        border = "green" if self.input_files else "#3B82F6"
        self.drop_frame.configure(border_color=border, fg_color="#F8FAFC")

    def handle_drop(self, event):
        try:
            if not event.data:
                return
            paths = self.tk.splitlist(event.data)
            valid_paths = []
            for path_str in paths:
                path_obj = Path(path_str)
                if path_obj.suffix.lower() in ['.docx', '.txt']:
                    valid_paths.append(path_obj)
                    
            if valid_paths:
                self.after(0, lambda: self.add_files(valid_paths))
            else:
                self.after(0, lambda: messagebox.showwarning("Warning", "Please drop .docx or .txt files."))
        except Exception as e:
            print(f"Drop error: {e}")
        finally:
            self.handle_drag_leave(None)

    def choose_files(self):
        paths = filedialog.askopenfilenames(
            title="Select MCQ Input Files",
            filetypes=[("Supported Files", "*.docx *.txt"), ("Word Documents", "*.docx"), ("Text Files", "*.txt")]
        )
        if paths:
            self.add_files([Path(p) for p in paths])

    def add_files(self, paths: List[Path]):
        for p in paths:
            if p not in self.input_files:
                self.input_files.append(p)
        count = len(self.input_files)
        self.file_info_var.set(f"Selected {count} files." if count > 1 else f"Selected: {self.input_files[0].name}")
        self.status_var.set(f"Ready to convert {count} files.")
        self.convert_btn.configure(state="normal")
        self.drop_frame.configure(border_color="green")
        
        mode = self.mode_var.get()
        mode_str = "Standardize Format" if mode == "standard" else "Only Renumber"
        added_list = ", ".join(f"{p.name}" for p in paths)
        
        msg = f"📂 Added to conversion queue:\n- {added_list}\n\n(Ready to process in {mode_str} mode)"
        actions = [
            {"text": "🚀 Convert Now", "command": self.start_conversion},
            {"text": "🧹 Clear", "command": lambda: self.clear_selection(notify=True)}
        ]
        self.sidebar.add_chat_message("Copilot", msg, actions=actions)

    def clear_selection(self, notify=True):
        self.input_files = []
        self.file_info_var.set("No files selected")
        self.status_var.set("Ready")
        self.convert_btn.configure(state="disabled")
        self.drop_frame.configure(border_color="#3B82F6")
        self.progress_bar.pack_forget()
        if notify:
            self.sidebar.add_chat_message("Copilot", "🧹 File queue cleared.")

    def start_conversion(self):
        if not self.input_files: return
        if len(self.input_files) == 1:
            input_file = self.input_files[0]
            output_path = filedialog.asksaveasfilename(
                title="Save Converted File",
                defaultextension=".docx",
                initialdir=str(input_file.parent),
                initialfile=input_file.stem + "_MCQ.docx",
                filetypes=[("Word Document", "*.docx")]
            )
            if not output_path: return
            targets = [(input_file, Path(output_path))]
        else:
            targets = [(f, f.with_name(f.stem + "_MCQ.docx")) for f in self.input_files]

        self.status_var.set("Converting...")
        self.convert_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        
        self.progress_bar.pack(pady=10, before=self.status_label)
        self.progress_bar.set(0)
        
        mode = self.mode_var.get()
        mode_str = "Standardize Format" if mode == "standard" else "Only Renumber"
        file_list = ", ".join(f"{f.name}" for f, _ in targets)
        self.sidebar.add_chat_message("Copilot", f"🚀 Starting conversion for:\n- {file_list}\n\n(Mode: {mode_str})")
        
        threading.Thread(target=self.process_batch, args=(targets,), daemon=True).start()

    def process_batch(self, targets: List[Tuple[Path, Path]]):
        success_count = 0
        total = len(targets)
        failed_files = []
        mode = self.mode_var.get()
        batch_details = []
        
        for i, (inp, out) in enumerate(targets):
            self.after(0, lambda idx=i+1, name=inp.name: self.status_var.set(f"Processing ({idx}/{total}): {name}"))
            progress_val = i / total
            self.after(0, lambda v=progress_val: self.progress_bar.set(v))
            
            try:
                ext = inp.suffix.lower()
                math_count = 0
                warnings_list = []
                if mode == "renumber":
                    if ext == '.docx':
                        renumber_docx_inplace(inp, out)
                    else:
                        renumber_txt_inplace(inp, out)
                    success_count += 1
                else:
                    questions = parse_docx(inp, warnings_list) if ext == '.docx' else parse_txt(inp, warnings_list)
                    if questions:
                        math_count = count_math_formulas(questions)
                        build_output_document(questions).save(str(out))
                        success_count += 1
                        
                        if warnings_list:
                            self.after(0, lambda name=inp.name, w=warnings_list: self.sidebar.add_chat_message(
                                "Copilot", self.format_warnings(name, w)
                            ))
                
                batch_details.append({
                    "filename": inp.name,
                    "math_count": math_count,
                    "warnings": warnings_list,
                    "status": "success"
                })
            except Exception as e:
                failed_files.append((inp.name, str(e)))
                print(f"Error processing {inp.name}: {e}")
                self.after(0, lambda name=inp.name, err=str(e): self.notify_error_in_chat(name, err))
                batch_details.append({
                    "filename": inp.name,
                    "math_count": 0,
                    "warnings": [],
                    "status": "error",
                    "error_msg": str(e)
                })

        self.after(0, lambda: self.progress_bar.set(1.0))

        if failed_files:
            err_msg = "\n".join([f"{name}: {err}" for name, err in failed_files[:5]])
            if len(failed_files) > 5:
                err_msg += f"\n... and {len(failed_files)-5} more."
            self.after(0, lambda msg=err_msg: self.show_error(f"Some files failed:\n{msg}"))

        self.after(0, lambda: self.finish_batch(success_count, total, batch_details))

    def format_warnings(self, filename: str, warnings: List[str]) -> str:
        warn_msg = f"⚠️ I detected some formatting issues in {filename} during conversion:\n\n"
        for w in warnings:
            cleaned_w = w.replace("Warning: ", "")
            warn_msg += f"- {cleaned_w}\n"
        warn_msg += "\nTip: Check the source document to make sure questions have at least 2 options and a valid Answer."
        return warn_msg

    def notify_error_in_chat(self, filename: str, err_msg: str):
        diagnostic = diagnose_error(err_msg)
        diagnostic_clean = diagnostic.replace("**", "")
        err_text = (
            f"❌ Failed to convert {filename}\n\n"
            f"Error Details: {err_msg}\n\n"
            f"Diagnosis & Actionable Advice:\n{diagnostic_clean}"
        )
        self.sidebar.add_chat_message("Copilot", err_text)

    def show_error(self, msg):
        messagebox.showerror("Failed", msg)
        self.status_var.set("An error occurred.")
        self.convert_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")
        self.progress_bar.pack_forget()

    def finish_batch(self, success, total, batch_details):
        self.status_var.set(f"Done! {success}/{total} files converted.")
        messagebox.showinfo("Success", f"Successfully converted {success} of {total} files.")
        
        msg_parts = [f"✅ Conversion Completed! Successfully processed {success} of {total} file(s).\n"]
        for detail in batch_details:
            name = detail["filename"]
            if detail["status"] == "success":
                math_info = ""
                if detail["math_count"] > 0:
                    math_info = f" (Preserved {detail['math_count']} math formulas)"
                
                if detail["warnings"]:
                    msg_parts.append(f"- {name}: Completed with format warnings.{math_info}")
                else:
                    msg_parts.append(f"- {name}: Completed cleanly.{math_info}")
            else:
                msg_parts.append(f"- {name}: ❌ Failed. Reason: {detail.get('error_msg', 'Unknown error')}")
                
        self.sidebar.add_chat_message("Copilot", "\n".join(msg_parts))
        
        self.clear_selection(notify=False)
        self.clear_btn.configure(state="normal")
        self.progress_bar.pack_forget()
