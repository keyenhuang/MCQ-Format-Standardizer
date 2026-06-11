import threading
import queue
import customtkinter as ctk
from config import get_config, save_config_value
from llm_client import call_llm_api_stream

class ChatSidebar:
    def __init__(self, parent_frame, app):
        self.parent = parent_frame
        self.app = app
        self.queue = queue.Queue()
        self.stream_active = False
        self.current_bubble = None
        self.setup_ui()
        
    def setup_ui(self):
        # Header (Copilot Title Bar)
        self.copilot_title_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.copilot_title_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        self.copilot_title = ctk.CTkLabel(self.copilot_title_frame, text="Copilot", font=("Segoe UI", 18, "bold"), text_color="#1E293B")
        self.copilot_title.pack(side="left")
        
        # Green online dot
        self.online_dot = ctk.CTkLabel(self.copilot_title_frame, text="●", text_color="#10B981", font=("Segoe UI", 10))
        self.online_dot.pack(side="left", padx=(5, 0))
        
        self.copilot_subtitle = ctk.CTkLabel(self.parent, text="AI assistant powered by CopilotKit", font=("Segoe UI", 11, "italic"), text_color="#64748B")
        self.copilot_subtitle.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Scrollable Chat Log container
        self.chat_scroll_frame = ctk.CTkScrollableFrame(self.parent, fg_color="transparent")
        self.chat_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Chat Input Box and Send Button Panel
        self.chat_input_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.chat_input_frame.pack(fill="x", padx=15, pady=15)
        
        self.chat_entry = ctk.CTkEntry(self.chat_input_frame, placeholder_text="Ask copilot...", font=("Segoe UI", 13),
                                       border_color="#CBD5E1", fg_color="#F8FAFC", text_color="#1E293B")
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda event: self.handle_chat_submit())
        
        self.chat_send_btn = ctk.CTkButton(self.chat_input_frame, text="Send", width=60, command=self.handle_chat_submit,
                                           fg_color="#2563EB", hover_color="#1D4ED8", text_color="white", corner_radius=8)
        self.chat_send_btn.pack(side="right")
        
        # Initial greeting from Copilot
        self.add_chat_message("Copilot", "Hi! I am your MCQ Copilot. Ask me how to use the converter, explain metrology questions, or type 'convert' to trigger processing!")

    def add_chat_message(self, sender: str, text: str, actions: list = None):
        row_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=6, padx=8)
        
        clean_text = text.replace("**", "").replace("__", "").strip()
        is_user = (sender.lower() == "user")
        bubble_color = "#E2E8F0" if is_user else "#3B82F6"
        text_color = "#1E293B" if is_user else "white"
        anchor_side = "right" if is_user else "left"
        anchor_align = "e" if is_user else "w"
        
        bubble = ctk.CTkFrame(row_frame, fg_color=bubble_color, corner_radius=12)
        bubble.pack(side=anchor_side, anchor=anchor_align)
        
        textbox = ctk.CTkTextbox(bubble, text_color=text_color, fg_color="transparent", 
                                 font=("Segoe UI", 13), wrap="word", width=300)
        textbox.pack(padx=10, pady=(6, 6))
        
        textbox.insert("0.0", clean_text)
        textbox.update_idletasks()
        
        display_lines_tuple = textbox._textbox.count("1.0", "end-1c", "displaylines")
        num_lines = display_lines_tuple[0] if display_lines_tuple else 1
        exact_height = num_lines * 22 + 20
        textbox.configure(height=exact_height)
        
        def _remeasure(tb=textbox):
            try:
                if not tb.winfo_exists():
                    return
                tb.update_idletasks()
                dl = tb._textbox.count("1.0", "end-1c", "displaylines")
                n = dl[0] if dl else 1
                h = n * 22 + 20
                if h != tb.cget("height"):
                    tb.configure(height=h)
            except Exception:
                pass
        self.app.after(100, _remeasure)
        
        # Aggressively remove internal scrollbars
        try:
            textbox.configure(scrollbar_button_color=bubble_color, scrollbar_button_hover_color=bubble_color)
        except Exception:
            pass
        if hasattr(textbox, '_scrollbar') and textbox._scrollbar:
            try:
                textbox._scrollbar.destroy()
            except Exception:
                try:
                    textbox._scrollbar.grid_forget()
                except Exception:
                    pass
        try:
            textbox._textbox.configure(yscrollcommand=lambda *a: None)
        except Exception:
            pass
            
        def _on_mousewheel(event):
            if self.chat_scroll_frame._parent_canvas.winfo_exists():
                self.chat_scroll_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
            
        textbox._textbox.bind("<MouseWheel>", _on_mousewheel)
        for seq in ("<Up>", "<Down>", "<Prior>", "<Next>"):
            textbox._textbox.bind(seq, lambda e: "break")
            
        textbox.configure(state="disabled")

        if actions and not is_user:
            actions_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            actions_frame.pack(fill="x", padx=12, pady=(0, 8))
            for act in actions:
                btn = ctk.CTkButton(actions_frame, text=act["text"], height=24, font=("Segoe UI", 11, "bold"),
                                    fg_color="#FFFFFF", text_color="#3B82F6", hover_color="#F1F5F9",
                                    corner_radius=6, command=act["command"])
                btn.pack(side="left", padx=(0, 5), pady=2)
                
        self.app.after(50, lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0))
        return textbox

    def show_thinking_indicator(self):
        self.thinking_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        self.thinking_frame.pack(fill="x", pady=6, padx=8)
        bubble = ctk.CTkFrame(self.thinking_frame, fg_color="#3B82F6", corner_radius=12)
        bubble.pack(side="left", anchor="w")
        self.thinking_label = ctk.CTkLabel(bubble, text="Thinking...", text_color="white", font=("Segoe UI", 13, "italic"))
        self.thinking_label.pack(padx=12, pady=8)
        self.app.after(50, lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0))
        self._animate_thinking(0)
        
    def _animate_thinking(self, dots):
        if hasattr(self, 'thinking_label') and self.thinking_label.winfo_exists():
            self.thinking_label.configure(text="Thinking" + "." * (dots % 4))
            self.app.after(400, self._animate_thinking, dots + 1)

    def hide_thinking_indicator(self):
        if hasattr(self, 'thinking_frame') and self.thinking_frame.winfo_exists():
            self.thinking_frame.destroy()

    def handle_chat_submit(self):
        msg = self.chat_entry.get().strip()
        if not msg or self.stream_active:
            return
            
        self.chat_entry.delete(0, "end")
        self.add_chat_message("User", msg)
        self.show_thinking_indicator()
        
        self.chat_send_btn.configure(state="disabled")
        self.chat_entry.configure(state="disabled")
        
        self.stream_active = True
        threading.Thread(target=self.generate_copilot_reply, args=(msg,), daemon=True).start()
        self.app.after(100, self.process_queue)

    def generate_copilot_reply(self, msg: str):
        msg_lower = msg.lower()
        
        if msg.startswith("/apikey "):
            key_part = msg[len("/apikey "):].strip()
            if save_config_value("API_KEY", key_part):
                self.queue.put(("text", "🔑 API Key saved securely!"))
            else:
                self.queue.put(("text", "❌ Failed to save API Key."))
            self.queue.put(("done", None))
            return
            
        if msg.startswith("/baseurl "):
            url_part = msg[len("/baseurl "):].strip()
            if save_config_value("BASE_URL", url_part):
                self.queue.put(("text", f"🔗 Base URL saved successfully!\n{url_part}"))
            else:
                self.queue.put(("text", "❌ Failed to save Base URL settings."))
            self.queue.put(("done", None))
            return
            
        if msg.startswith("/model "):
            model_part = msg[len("/model "):].strip()
            if save_config_value("MODEL", model_part):
                self.queue.put(("text", f"🎯 Model name saved successfully!\n{model_part}"))
            else:
                self.queue.put(("text", "❌ Failed to save model settings."))
            self.queue.put(("done", None))
            return
            
        if "clear" in msg_lower:
            self.app.after(0, lambda: self.app.clear_selection(notify=False))
            self.queue.put(("text", "🧹 File list cleared! You can now drag and drop new files."))
            self.queue.put(("done", None))
            return
            
        if "renumber" in msg_lower:
            self.app.after(0, lambda: self.app.mode_var.set("renumber"))
            self.queue.put(("text", "🔄 Switched conversion mode to: Only Renumber."))
            self.queue.put(("done", None))
            return
            
        if "standard" in msg_lower:
            self.app.after(0, lambda: self.app.mode_var.set("standard"))
            self.queue.put(("text", "📋 Switched conversion mode to: Standardize Format."))
            self.queue.put(("done", None))
            return
            
        if "convert" in msg_lower:
            if not self.app.input_files:
                self.queue.put(("text", "⚠️ You haven't selected any files yet! Please drag and drop or browse files first, then ask me to convert."))
            else:
                self.queue.put(("text", f"🚀 Starting conversion for {len(self.app.input_files)} file(s)..."))
                self.app.after(0, self.app.start_conversion)
            self.queue.put(("done", None))
            return
            
        if "help" in msg_lower:
            help_text = (
                "Here is how to use the MCQ Converter:\n"
                "1. Drag & drop .docx or .txt files into the left box (or click to browse).\n"
                "2. Choose either 'Standardize Format' or 'Only Renumber'.\n"
                "3. Click 'Convert All' to process the files.\n\n"
                "Quick Chat Commands:\n"
                "- clear: Clear the selected file list.\n"
                "- standard: Switch to Standardize Format mode.\n"
                "- renumber: Switch to Only Renumber mode.\n"
                "- convert: Start the conversion.\n\n"
                "LLM Config Commands:\n"
                "- /apikey <key>: Set API Key securely.\n"
                "- /baseurl <url>: Set custom API base URL.\n"
                "- /model <name>: Set model name."
            )
            self.queue.put(("text", help_text))
            self.queue.put(("done", None))
            return

        config = get_config()
        api_key = config.get("API_KEY")
        
        if not api_key:
            response = (
                "⚠️ API Key not found.\n\n"
                "To enable the AI model for Q&A, please type '/apikey <your_key>' in this chat box to save it securely.\n\n"
                "(Basic local commands like clear, convert, standard, renumber, and help are still available without a key!)"
            )
            self.queue.put(("text", response))
            self.queue.put(("done", None))
            return

        context = ""
        if self.app.input_files:
            file_names = ", ".join(f.name for f in self.app.input_files)
            context = f"[Context: The user has loaded these files into the MCQ Converter: {file_names}]\n"
        
        prompt = f"{context}User message: {msg}"
        
        for token in call_llm_api_stream(prompt, config):
            self.queue.put(("token", token))
            
        self.queue.put(("done", None))

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == "text":
                    self.hide_thinking_indicator()
                    self.add_chat_message("Copilot", data)
                elif msg_type == "token":
                    self.hide_thinking_indicator()
                    if self.current_bubble is None:
                        self.current_bubble = self.create_active_stream_bubble()
                    
                    self.current_bubble.configure(state="normal")
                    self.current_bubble.insert("end", data)
                    self.current_bubble.configure(state="disabled")
                    self.current_bubble.update_idletasks()
                    
                    dl = self.current_bubble._textbox.count("1.0", "end-1c", "displaylines")
                    n = dl[0] if dl else 1
                    h = n * 22 + 20
                    self.current_bubble.configure(height=h)
                    self.chat_scroll_frame._parent_canvas.yview_moveto(1.0)
                    
                elif msg_type == "done":
                    self.hide_thinking_indicator()
                    self.current_bubble = None
                    self.stream_active = False
                    self.chat_send_btn.configure(state="normal")
                    self.chat_entry.configure(state="normal")
                    self.chat_entry.focus()
                    return
        except queue.Empty:
            if self.stream_active:
                self.app.after(50, self.process_queue)

    def create_active_stream_bubble(self):
        row_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=6, padx=8)
        bubble = ctk.CTkFrame(row_frame, fg_color="#3B82F6", corner_radius=12)
        bubble.pack(side="left", anchor="w")
        
        textbox = ctk.CTkTextbox(bubble, text_color="white", fg_color="transparent", 
                                 font=("Segoe UI", 13), wrap="word", width=300, height=40)
        textbox.pack(padx=10, pady=(6, 6))
        
        try:
            textbox.configure(scrollbar_button_color="#3B82F6", scrollbar_button_hover_color="#3B82F6")
        except Exception:
            pass
        if hasattr(textbox, '_scrollbar') and textbox._scrollbar:
            try:
                textbox._scrollbar.destroy()
            except Exception:
                textbox._scrollbar.grid_forget()
        try:
            textbox._textbox.configure(yscrollcommand=lambda *a: None)
        except Exception:
            pass
            
        def _on_mousewheel(event):
            if self.chat_scroll_frame._parent_canvas.winfo_exists():
                self.chat_scroll_frame._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"
            
        textbox._textbox.bind("<MouseWheel>", _on_mousewheel)
        for seq in ("<Up>", "<Down>", "<Prior>", "<Next>"):
            textbox._textbox.bind(seq, lambda e: "break")
            
        textbox.configure(state="disabled")
        return textbox
