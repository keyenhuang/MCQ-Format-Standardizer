# MCQ Format Standardizer

[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![CI](https://github.com/keyenhuang/MCQ-Format-Standardizer/actions/workflows/ci.yml/badge.svg)](https://github.com/keyenhuang/MCQ-Format-Standardizer/actions/workflows/ci.yml)

A comprehensive tool for converting and standardizing MCQ (Multiple Choice Question) documents from various formats into a consistent, editable format suitable for educational and assessment purposes.

## Overview

**MCQ Format Standardizer** is a powerful desktop application that helps educators, content creators, and administrators process MCQ questions efficiently. The tool can:

- Extract MCQ questions from Word documents (.docx) and text files (.txt)
- Standardize question formatting and structure
- Batch process multiple files simultaneously
- Provide AI-powered assistance for question explanation and guidance
- Support both full conversion and simple renumbering operations

## Key Features

### Document Processing
- **Multi-format Support**: Convert .docx and .txt files containing MCQ questions
- **Batch Processing**: Process multiple files at once for increased productivity
- **Flexible Modes**: Choose between full standardization or simple renumbering

### Intelligent GUI Interface
- **Drag-and-Drop**: Simple file selection with visual feedback
- **Quick Actions**: Pre-built shortcuts for common tasks
- **Real-time Status**: Progress tracking and error notifications
- **AI Assistant**: Built-in Q&A system for question explanation

### Advanced Capabilities
- **Error Recovery**: Smart error detection with actionable advice
- **Configurable Output**: Customizable formatting options
- **Secure Storage**: Encrypted API key management
- **Extensive Logging**: Detailed processing logs for debugging

## Technology Stack

- **Python 3.7+**: Core programming language
- **Tkinter/CTkinter**: GUI framework
- **python-docx**: Word document manipulation
- **keyring**: Secure password management
- **OpenAI API/Groq**: AI-powered chat assistance

## Installation

### Prerequisites
```bash
python 3.7 or higher
pip (for package management)
Administrator privileges (for file system access)
```

### Step-by-Step Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd mcq-format-standardizer
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up API key** (for AI features):
```bash
# Method 1: Environment variables (recommended)
export MCQ_API_KEY="your-api-key"
export MCQ_BASE_URL="https://api.groq.com/openai/v1"

# Method 2: GUI setup (recommended for security)
Run the application and use '/apikey your-key' command in the chat
```

4. **Run the application**:
```bash
# Command Line Interface
python main.py input.docx output.docx

# Graphical User Interface
python main.py --gui
```

## Usage Guide

### Command Line Interface

The application supports two main modes of operation:

#### Standard Conversion
```bash
python main.py input_file.docx output_file.docx
```

#### Only Renumber
```bash
python main.py input_file.txt --only-renumber
```

#### Display Help
```bash
python main.py --help
```

### Graphical User Interface

1. **Launch the application**:
```bash
python main.py --gui
```

2. **Basic workflow**:
   - Drag and drop .docx or .txt files into the left panel
   - Select "Standardize Format" or "Only Renumber" mode
   - Click "Convert All" to process files
   - Monitor progress in the status area

3. **Chat with AI Assistant**:
   - Use the chat sidebar for Q&A
   - Type commands like `/help`, `/convert`, `/apikey`
   - Get explanations for complex questions

### Chat Commands

#### Basic Commands
- `/help`: Display help information
- `/convert`: Start file conversion
- `/standard`: Switch to standardization mode
- `/renumber`: Switch to renumber mode
- `/clear`: Clear file list

#### LLM Configuration
- `/apikey <your-key>`: Set API key securely
- `/baseurl <url>`: Set custom API base URL

## File Formats Supported

### Input Formats
- **Word Documents (.docx)**: Full MCQ question extraction
- **Text Files (.txt)**: Plain text question processing

### Output Format
- **Word Documents (.docx)**: Standardized MCQ format with proper formatting

## Configuration

### API Configuration
The application uses Groq's LLaMA models by default. For custom setups:

1. **Environment Variables** (recommended):
```bash
export MCQ_API_KEY="your-groq-api-key"
export MCQ_BASE_URL="https://api.groq.com/openai/v1"
export MCQ_MODEL="llama-3.3-70b-versatile"
```

2. **GUI Configuration**:
   - Click the chat button to open AI assistant
   - Use `/apikey your-key` to set securely
   - Use `/baseurl` if using a different provider

### Application Settings
- **Configuration File**: `config.json` stores application settings
- **API Key Storage**: Uses system keyring for secure storage
- **Logging**: Detailed logs available for troubleshooting

## Project Structure

```
mcq-format-standardizer/
├── main.py                    # Entry point and CLI interface
├── config.py                  # Configuration management
├── logger.py                  # Logging system
├── llm_client.py              # AI chat integration
├── .env.example               # Environment variable template
├── .gitignore                 # Version control ignored files
├── README.md                  # This documentation
├── requirements.txt           # Python dependencies
├── formatter/                 # Output document formatting
│   ├── docx_formatter.py      # Word document builder
│   └── __init__.py            # Module initialization
├── gui/                       # Graphical user interface
│   ├── app.py                 # Main application window
│   ├── chat_sidebar.py        # AI chat interface
│   └── __init__.py            # Module initialization
└── parser/                    # Document parsing and processing
    ├── engine.py              # Core parsing engine
    ├── models.py              # Data models
    ├── regex.py               # Regular expression patterns
    ├── text_utils.py          # Text processing utilities
    ├── txt_parser.py          # Text file parser
    ├── docx_parser.py          # Word document parser
    └── xml_utils.py           # XML document utilities
```

## Features by Module

### Parser Module
- **docx_parser.py**: Extracts questions from .docx files using document structure analysis
- **txt_parser.py**: Processes plain text files with pattern matching
- **engine.py**: Core question extraction and validation engine
- **models.py**: Data structures for question representation

### Formatter Module
- **docx_formatter.py**: Builds standardized .docx documents from parsed questions

### GUI Module
- **app.py**: Main application window with all UI components
- **chat_sidebar.py**: AI assistant interface for question help and guidance

### Utilities
- **llm_client.py**: AI chat integration for question explanation
- **logger.py**: Comprehensive logging system
- **config.py**: Secure configuration management

## Development

### Contributing
1. **Fork the repository**
2. **Create a feature branch**
```bash
git checkout -b feature/your-name/feature-name
```
3. **Make your changes**
4. **Test your changes**
5. **Commit with descriptive message**
```bash
git add .
git commit -m "feat: add new feature description"
```
6. **Push to your branch**
```bash
git push origin feature/your-name/feature-name
```
7. **Submit a pull request**

### Running Tests
Currently, the project does not have a formal test suite. For manual testing:

```bash
# Run the application in different modes
python main.py --gui          # GUI mode
python main.py input.docx      # CLI conversion mode
python main.py input.docx --r # Renumber mode
```

### Development Setup
For development and enhancement:

1. **Python Environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Code Style**:
   - PEP 8 compliant
   - Type hints where appropriate
   - Comprehensive docstrings

3. **Security Best Practices**:
   - Never commit API keys
   - Use environment variables for sensitive data
   - Implement proper error handling

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Check if key is correctly set via `/apikey` command
   - Verify environment variables are set
   - Ensure API key has necessary permissions

2. **File Conversion Fails**
   - Try different input formats
   - Check if document structure is compatible
   - Review error messages in the application logs

3. **Application Doesn't Start**
   - Ensure all Python dependencies are installed
   - Check for port conflicts if running multiple instances
   - Verify file system permissions

### Getting Help

1. **Chat with AI Assistant**: Use the chat sidebar for instant help
2. **Check Application Logs**: Review logs in the application for detailed error information
3. **Environment Variables**: Use `.env.example` as a template for configuration

## License

[MIT License](LICENSE)

## Contact

For issues, questions, or feature requests:
- Open an issue in the repository
- Contact through the application's built-in support system
- Check the documentation for common solutions

## Acknowledgements

Special thanks to all contributors and users who have helped improve this application.

---

**Version**: 1.0.0  
**Author**: keyenhuang