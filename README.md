# MCQ Format Standardizer

[![CI](https://github.com/keyenhuang/MCQ-Format-Standardizer/actions/workflows/ci.yml/badge.svg)](https://github.com/keyenhuang/MCQ-Format-Standardizer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI: CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)

A modern, high-performance desktop application for batch parsing, standardizing, and renumbering Multiple Choice Question (MCQ) documents from Word (`.docx`) and Plain Text (`.txt`) files, with native support for OpenXML math formulas, full-width Chinese character normalization, and an integrated AI Copilot assistant.

---

## 🌟 Key Features

| Feature | Description |
| :--- | :--- |
| **📑 Multi-Format Parsing** | Extracts MCQs seamlessly from Word (`.docx`) and Plain Text (`.txt`) files. |
| **📐 Math Formula Preservation** | Preserves embedded OpenXML MathOMath formulas (`x^2 + y^2 = z^2`) in Word documents without corruption. |
| **🔤 Unicode Normalization** | Automatically normalizes full-width Chinese numbers (`１．`), options (`Ａ．`), and brackets (`（Ｂ）`) to standard ASCII. |
| **🎨 Modern CustomTkinter GUI** | Built with CustomTkinter, featuring Dark/Light/System theme toggling, drag-and-drop file queue, segmented mode controls, and card-based layout. |
| **🤖 Built-in AI Copilot** | Streamed AI assistant powered by Groq / OpenAI compatible APIs for file guidance, Q&A, and quick slash commands (`/apikey`, `/baseurl`, `/model`). |
| **⚡ Dual Operation Modes** | Choose between **Standardize Format** (full restructuring) and **Only Renumber** (in-place index re-sequencing). |
| **📦 Standalone Executable** | Includes `build_exe.py` PyInstaller script for single-click Windows `.exe` packaging. |

---

## 🖥️ UI Overview & CustomTkinter Modernization

The application UI leverages CustomTkinter for a sleek, responsive user experience:

- **Theme Mode Switcher**: Seamlessly toggle between **System**, **Light**, and **Dark** appearance modes.
- **Segmented Control**: Easily switch between `Standardize Format` and `Only Renumber` conversion modes.
- **Drag & Drop Card**: Reactive drop zone with visual color feedback on file hover and drop.
- **Copilot Sidebar**: Chat sidebar with streamed token animations, thinking indicators, and quick action chips.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- `pip` package manager

### Step-by-Step Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/keyenhuang/MCQ-Format-Standardizer.git
   cd MCQ-Format-Standardizer
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **(Optional) Install development & testing dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

---

## 🚀 Usage Guide

### 1. Graphical User Interface (GUI Mode)

Launch the desktop GUI application:
```bash
python main.py --gui
# or simply:
python main.py
```

#### Basic Workflow:
1. **Add Files**: Drag & drop `.docx` or `.txt` files into the left drag-and-drop card, or click to browse.
2. **Select Mode**: Use the segmented button to choose **Standardize Format** or **Only Renumber**.
3. **Convert**: Click **Convert All** to execute batch processing.
4. **Chat with Copilot**: Use the right sidebar to set API keys, ask questions, or run quick commands.

---

### 2. Command Line Interface (CLI Mode)

#### Standard Conversion
Convert and standardize formatting into a new `.docx` document:
```bash
python main.py input_file.docx output_file.docx
```

#### Text File Conversion
Convert a plain text `.txt` question bank into a standardized `.docx` file:
```bash
python main.py input_file.txt output_file.docx
```

#### In-place Renumbering Only
Renumber questions sequentially (`1.`, `2.`, `3.`) while preserving existing document styling:
```bash
python main.py input_file.docx output_file.docx --only-renumber
```

---

## 🤖 AI Copilot & Slash Commands

The built-in Copilot supports instant local quick actions and LLM streaming:

| Command | Type | Description |
| :--- | :--- | :--- |
| `/apikey <your_key>` | LLM Config | Saves API key securely to system keyring. |
| `/baseurl <url>` | LLM Config | Customizes LLM base URL (e.g. Groq, OpenAI, Ollama). |
| `/model <name>` | LLM Config | Sets target LLM model name (default: `llama-3.3-70b-versatile`). |
| `convert` | Local Action | Triggers file conversion for currently loaded queue. |
| `clear` | Local Action | Clears the current file queue. |
| `standard` | Local Action | Switches mode to Standardize Format. |
| `renumber` | Local Action | Switches mode to Only Renumber. |
| `help` | Local Action | Displays quick help and command list. |

---

## 📦 Packaging Standalone Windows `.exe`

To build a standalone executable for Windows (without requiring a Python installation on user machines):

```bash
python build_exe.py
```

The output executable will be generated in `dist/MCQFormatStandardizer/`.

---

## 🧪 Running Unit Tests

Run the test suite using `pytest` or Python's native `unittest`:

```bash
# Using pytest
pytest tests/

# Using unittest
python -m unittest discover tests
```

---

## 📁 Project Architecture

```
MCQ-Format-Standardizer/
├── main.py                    # Application entry point (CLI & GUI dispatch)
├── build_exe.py               # PyInstaller standalone build script
├── config.py                  # App configuration & keyring management
├── logger.py                  # Centralized logging setup
├── llm_client.py              # LLM streaming API client
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Testing & dev dependencies
│
├── parser/                    # MCQ Parsing Engine
│   ├── engine.py              # Core parser, NFKC normalization & error diagnostics
│   ├── docx_parser.py         # OpenXML Word document parser & in-place renumbering
│   ├── txt_parser.py          # Plain text parser
│   ├── regex.py               # Question & Option regular expressions
│   ├── models.py              # Question data models
│   └── xml_utils.py           # Word OpenXML node processing & math formula handling
│
├── formatter/                 # Output Document Generator
│   └── docx_formatter.py      # Standardized Word document builder
│
├── gui/                       # CustomTkinter GUI Components
│   ├── app.py                 # Main application window & Theme Switcher
│   ├── drop_zone.py           # Drag and Drop file card
│   ├── chat_sidebar.py        # Copilot AI chat sidebar
│   ├── file_manager.py        # File queue manager
│   └── converter.py           # Background conversion thread worker
│
└── tests/                     # Automated Test Suite
    └── test_parser.py         # Unit tests for parser engine
```

---

## 📄 License

Distributed under the [MIT License](LICENSE). Copyright (c) 2026 keyenhuang.