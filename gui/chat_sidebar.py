import threading
import queue
import customtkinter as ctk
from config import get_config, save_config_value
from llm_client import call_llm_api_stream
from logger import get_logger

logger = get_logger()

LINE_HEIGHT_PX = 22
BUBBLE_PADDING = 20
BUBBLE_WIDTH = 300
FONT_SPEC = ("Segoe UI", 13)


def _make_mousewheel_handler(scroll_frame):
    def _on_mousewheel(event):
        try:
            if scroll_frame._parent_canvas.winfo_exists():
                scroll_frame._parent_canvas.yview_scroll(
                    int(-1 * (event.delta / 120)), "units"
                )
        except (AttributeError, OSError):
            pass
        return "break"
    return _on_mousewheel


def _disable_internal_scrollbar(textbox, bg_color):
    try:
        textbox.configure(
            scrollbar_button_color=bg_color,
            scrollbar_button_hover_color=bg_color
        )
    except (AttributeError, OSError):
        pass
    sb = getattr(textbox, '_scrollbar', None)
    if sb:
        try:
            sb.destroy()
        except (AttributeError, OSError):
            try:
                sb.grid_forget()
            except (AttributeError, OSError):
                pass
    try:
        textbox._textbox.configure(yscrollcommand=lambda *a: None)
    except (AttributeError, OSError):
        pass


def _bind_scroll_redirect(textbox, scroll_frame):
    mw_handler = _make_mousewheel_handler(scroll_frame)
    textbox._textbox.bind("<MouseWheel>", mw_handler)
    for seq in ("<Up>", "<Down>", "<Prior>", "<Next>"):
        textbox._textbox.bind(seq, lambda e: "break")


def _remeasure_after(app, textbox, delay=100):
    def _remeasure():
        try:
            if not textbox.winfo_exists():
                return
            textbox.update_idletasks()
            result = textbox._textbox.count("1.0", "end-1c", "displaylines")
            n = result[0] if result else 1
            h = n * LINE_HEIGHT_PX + BUBBLE_PADDING
            if h != textbox.cget("height"):
                textbox.configure(height=h)
        except (AttributeError, OSError, IndexError, TypeError):
            pass
    app.after(delay, _remeasure)


def _compute_textbox_height(textbox):
    result = textbox._textbox.count("1.0", "end-1c", "displaylines")
    n = result[0] if result else 1
    return n * LINE_HEIGHT_PX + BUBBLE_PADDING


class ChatSidebar:
    def __init__(self, parent_frame, app):
        self.parent = parent_frame
        self.app = app
        self.queue = queue.Queue()
        self.stream_active = False
        self.current_bubble = None
        self.setup_ui()

    # --- UI Setup ---

    def setup_ui(self):
        title_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            title_frame, text="Copilot",
            font=("Segoe UI", 18, "bold"), text_color=("#1E293B", "#F8FAFC")
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame, text="\u25cf", text_color="#10B981",
            font=("Segoe UI", 10)
        ).pack(side="left", padx=(5, 0))

        ctk.CTkLabel(
            self.parent, text="AI assistant powered by CopilotKit",
            font=("Segoe UI", 11, "italic"), text_color=("#64748B", "#94A3B8")
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.chat_scroll_frame = ctk.CTkScrollableFrame(
            self.parent, fg_color="transparent"
        )
        self.chat_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        input_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        input_frame.pack(fill="x", padx=15, pady=15)

        self.chat_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Ask copilot...",
            font=FONT_SPEC,
            border_color=("#CBD5E1", "#475569"),
            fg_color=("#F8FAFC", "#0F172A"),
            text_color=("#1E293B", "#F8FAFC")
        )
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", lambda event: self.handle_chat_submit())

        self.chat_send_btn = ctk.CTkButton(
            input_frame, text="Send", width=60,
            command=self.handle_chat_submit,
            fg_color="#2563EB", hover_color="#1D4ED8",
            text_color="white", corner_radius=8
        )
        self.chat_send_btn.pack(side="right")

        self.add_chat_message(
            "Copilot",
            "Hi! I am your MCQ Copilot. Ask me how to use the converter, "
            "explain metrology questions, or type 'convert' to trigger processing!"
        )

    # --- Message Bubble ---

    def add_chat_message(self, sender: str, text: str, actions: list = None):
        row_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=6, padx=8)

        is_user = (sender.lower() == "user")
        bubble_color = ("#E2E8F0", "#334155") if is_user else ("#2563EB", "#1D4ED8")
        text_color = ("#1E293B", "#F8FAFC") if is_user else "white"

        side = "right" if is_user else "left"
        align = "e" if is_user else "w"

        bubble = ctk.CTkFrame(row_frame, fg_color=bubble_color, corner_radius=12)
        bubble.pack(side=side, anchor=align)

        textbox = ctk.CTkTextbox(
            bubble,
            text_color=text_color, fg_color="transparent",
            font=FONT_SPEC, wrap="word", width=BUBBLE_WIDTH
        )
        textbox.pack(padx=10, pady=(6, 6))
        textbox.insert("0.0", text.strip())
        textbox.update_idletasks()

        h = _compute_textbox_height(textbox)
        textbox.configure(height=h)

        _remeasure_after(self.app, textbox)
        _disable_internal_scrollbar(textbox, bubble_color)
        _bind_scroll_redirect(textbox, self.chat_scroll_frame)

        textbox.configure(state="disabled")

        if actions and not is_user:
            actions_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            actions_frame.pack(fill="x", padx=12, pady=(0, 8))
            for act in actions:
                btn = ctk.CTkButton(
                    actions_frame,
                    text=act["text"], height=24,
                    font=("Segoe UI", 11, "bold"),
                    fg_color="#FFFFFF", text_color="#3B82F6",
                    hover_color="#F1F5F9", corner_radius=6,
                    command=act["command"]
                )
                btn.pack(side="left", padx=(0, 5), pady=2)

        self._scroll_to_bottom()
        return textbox

    def create_active_stream_bubble(self):
        row_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=6, padx=8)
        bubble = ctk.CTkFrame(row_frame, fg_color="#3B82F6", corner_radius=12)
        bubble.pack(side="left", anchor="w")

        textbox = ctk.CTkTextbox(
            bubble,
            text_color="white", fg_color="transparent",
            font=FONT_SPEC, wrap="word",
            width=BUBBLE_WIDTH, height=40
        )
        textbox.pack(padx=10, pady=(6, 6))

        _disable_internal_scrollbar(textbox, "#3B82F6")
        _bind_scroll_redirect(textbox, self.chat_scroll_frame)

        textbox.configure(state="disabled")
        return textbox

    def _scroll_to_bottom(self):
        self.app.after(
            50,
            lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0)
        )

    # --- Thinking Indicator ---

    def show_thinking_indicator(self):
        self.thinking_frame = ctk.CTkFrame(
            self.chat_scroll_frame, fg_color="transparent"
        )
        self.thinking_frame.pack(fill="x", pady=6, padx=8)
        bubble = ctk.CTkFrame(
            self.thinking_frame, fg_color="#3B82F6", corner_radius=12
        )
        bubble.pack(side="left", anchor="w")
        self.thinking_label = ctk.CTkLabel(
            bubble, text="Thinking",
            text_color="white", font=("Segoe UI", 13, "italic")
        )
        self.thinking_label.pack(padx=12, pady=8)
        self._scroll_to_bottom()
        self._animate_thinking(0)

    def _animate_thinking(self, dots):
        try:
            if hasattr(self, 'thinking_label') and self.thinking_label.winfo_exists():
                self.thinking_label.configure(text="Thinking" + "." * (dots % 4))
                self.app.after(400, self._animate_thinking, dots + 1)
        except (AttributeError, OSError):
            pass

    def hide_thinking_indicator(self):
        try:
            if hasattr(self, 'thinking_frame') and self.thinking_frame.winfo_exists():
                self.thinking_frame.destroy()
        except (AttributeError, OSError):
            pass

    # --- Chat Submission ---

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
        threading.Thread(
            target=self.generate_copilot_reply, args=(msg,), daemon=True
        ).start()
        self.app.after(100, self.process_queue)

    def generate_copilot_reply(self, msg: str):
        msg_lower = msg.lower()
        config = get_config()

        # Handle slash commands
        if msg.startswith("/apikey "):
            key = msg[len("/apikey "):].strip()
            if save_config_value("API_KEY", key):
                self.queue.put(("text", "API Key saved securely!"))
            else:
                self.queue.put(("text", "Failed to save API Key."))
            self.queue.put(("done", None))
            return

        if msg.startswith("/baseurl "):
            url = msg[len("/baseurl "):].strip()
            if save_config_value("BASE_URL", url):
                self.queue.put(("text", f"Base URL saved successfully!\n{url}"))
            else:
                self.queue.put(("text", "Failed to save Base URL."))
            self.queue.put(("done", None))
            return

        if msg.startswith("/model "):
            model = msg[len("/model "):].strip()
            if save_config_value("MODEL", model):
                self.queue.put(("text", f"Model name saved successfully!\n{model}"))
            else:
                self.queue.put(("text", "Failed to save model settings."))
            self.queue.put(("done", None))
            return

        # Handle quick commands
        cmd_map = {
            "clear": (lambda: self.app.clear_selection(notify=False),
                      "File list cleared! You can now drag and drop new files."),
            "renumber": (lambda: self.app.mode_var.set("renumber"),
                         "Switched conversion mode to: Only Renumber."),
            "standard": (lambda: self.app.mode_var.set("standard"),
                         "Switched conversion mode to: Standardize Format."),
        }
        for keyword, (action, response) in cmd_map.items():
            if keyword in msg_lower:
                self.app.after(0, action)
                self.queue.put(("text", response))
                self.queue.put(("done", None))
                return

        if "convert" in msg_lower:
            if self.app.file_manager.count == 0:
                self.queue.put((
                    "text",
                    "You haven't selected any files yet! "
                    "Please drag and drop or browse files first, then ask me to convert."
                ))
            else:
                self.queue.put((
                    "text",
                    f"Starting conversion for {self.app.file_manager.count} file(s)..."
                ))
                self.app.after(0, self.app.start_conversion)
            self.queue.put(("done", None))
            return

        if "help" in msg_lower:
            help_text = (
                "Here is how to use the MCQ Format Standardizer:\n"
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

        api_key = config.get("API_KEY")
        if not api_key:
            self.queue.put((
                "text",
                "API Key not found.\n\n"
                "To enable the AI model for Q&A, please type '/apikey <your_key>' "
                "in this chat box to save it securely.\n\n"
                "(Basic local commands like clear, convert, standard, renumber, "
                "and help are still available without a key!)"
            ))
            self.queue.put(("done", None))
            return

        context = ""
        if self.app.file_manager.count > 0:
            names = ", ".join(f.name for f in self.app.file_manager.input_files)
            context = f"[Context: The user has loaded these files into the MCQ Format Standardizer: {names}]\n"

        prompt = f"{context}User message: {msg}"

        for token in call_llm_api_stream(prompt, config):
            self.queue.put(("token", token))

        self.queue.put(("done", None))

    # --- Queue Processing ---

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

                    h = _compute_textbox_height(self.current_bubble)
                    self.current_bubble.configure(height=h)
                    self._scroll_to_bottom()

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
