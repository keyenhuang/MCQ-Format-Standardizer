#!/usr/bin/env python3
"""
MCQ Converter - Advanced Batch Pro
==================================
Enhanced version with flexible input parsing and strict output formatting.
Supports Drag & Drop and Batch Processing.
"""

import re
import sys
import io
import os
import threading
import copy
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from docx import Document

class TkinterDnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)



# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# LLM Config Helper Functions
# ---------------------------------------------------------------------------

_CONFIG_CACHE = None

def _get_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config = {
        "API_KEY": "",
        "BASE_URL": "https://api.groq.com/openai/v1",
        "MODEL": "llama-3.3-70b-versatile"
    }
    config_path = Path("config.json")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                key = data.get("API_KEY")
                if key:
                    config["API_KEY"] = key.strip()
                if data.get("BASE_URL"):
                    config["BASE_URL"] = data["BASE_URL"].strip()
                if data.get("MODEL"):
                    config["MODEL"] = data["MODEL"].strip()
        except Exception as e:
            print(f"Warning: Failed to load config.json: {e}")
            
    _CONFIG_CACHE = config
    return config

def _save_config_value(key_name, value):
    global _CONFIG_CACHE
    config_path = Path("config.json")
    try:
        data = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[key_name] = value.strip() if isinstance(value, str) else value
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
            
        # Update cache if write was successful
        if _CONFIG_CACHE is not None:
            _CONFIG_CACHE[key_name] = data[key_name]
            
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def call_llm_api(prompt: str, config: dict) -> str:
    import urllib.request
    import urllib.error
    
    api_key = config.get("API_KEY", "")
    base_url = config.get("BASE_URL", "").rstrip("/")
    model = config.get("MODEL", "llama-3.3-70b-versatile")
    
    if not api_key:
        return "⚠️ API Key is not set yet! Use `/apikey <key>` to set it."
        
    if not base_url:
        return "⚠️ Base URL is not set. Use `/baseurl <url>` to set it."
        
    system_instruction = (
        "You are MCQ Copilot, a friendly and intelligent AI assistant built into the MCQ Batch Converter app. "
        "Your goal is to assist users with file conversions, explain concepts, and provide helpful guidance. "
        "CRITICAL: This chat UI does NOT support Markdown. Do NOT use asterisks (**) for bold, or underscores (_) for italics. "
        "Keep your answers plain text, clear, concise, and engaging. You can use emojis to express emotions! "
        "If the user asks to convert, remind them they can click the Convert button or use quick actions. "
        "Always reply in English."
    )
    
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
    }
        
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {api_key}",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    )
    
    print(f"\n[LLM Request] Model: {model}, URL: {url}")
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text = res_data['choices'][0]['message']['content']
            return text
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "too many requests" in err_str.lower():
            return (
                "⚠️ **API Rate Limit Exceeded (HTTP 429)**:\n\n"
                "Please wait a few seconds and try again, or consider using a different model/provider."
            )
        elif "403" in err_str:
            return "❌ **Forbidden (HTTP 403)**: Access denied. Please ensure your API key and base URL are correct."
        elif "400" in err_str:
            return f"❌ **Bad Request (HTTP 400)**: Details: {err_str}"
        elif "401" in err_str:
            return "❌ **Unauthorized (HTTP 401)**: Invalid API Key."
        return f"Error communicating with LLM API: {err_str}"


# ---------------------------------------------------------------------------
# XML Helper Functions for Formula/Format Preservation
# ---------------------------------------------------------------------------

def _create_run_xml(text):
    from docx.oxml import OxmlElement
    r = OxmlElement('w:r')
    t = OxmlElement('w:t')
    t.text = text
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t)
    return r

def _create_br_xml():
    from docx.oxml import OxmlElement
    r = OxmlElement('w:r')
    br = OxmlElement('w:br')
    r.append(br)
    return r

def _get_para_xml_elements(para):
    elements = []
    for child in para._p:
        if child.tag.endswith('}pPr'):
            continue
        elements.append(copy.deepcopy(child))
    return elements

def _strip_xml_prefix(elements, count):
    if count <= 0:
        return
    for elem in elements:
        for text_node in elem.iter():
            if text_node.tag.endswith('}t'):
                node_text = text_node.text or ""
                node_len = len(node_text)
                if node_len >= count:
                    text_node.text = node_text[count:]
                    return
                else:
                    text_node.text = ""
                    count -= node_len

def _split_xml_elements_by_separator(elements, sep="|"):
    options_xml = []
    current_xml = []
    for elem in elements:
        text_parts = []
        for t in elem.iter():
            if t.tag.endswith('}t'):
                text_parts.append(t.text or "")
        elem_text = "".join(text_parts)
        if sep in elem_text:
            text_nodes = [t for t in elem.iter() if t.tag.endswith('}t')]
            if len(text_nodes) == 1:
                t_node = text_nodes[0]
                t_text = t_node.text or ""
                t_parts = t_text.split(sep)
                t_node.text = t_parts[0]
                current_xml.append(elem)
                options_xml.append(current_xml)
                for part in t_parts[1:-1]:
                    new_elem = copy.deepcopy(elem)
                    new_t = [t for t in new_elem.iter() if t.tag.endswith('}t')][0]
                    new_t.text = part
                    options_xml.append([new_elem])
                new_elem = copy.deepcopy(elem)
                new_t = [t for t in new_elem.iter() if t.tag.endswith('}t')][0]
                new_t.text = t_parts[-1]
                current_xml = [new_elem]
            else:
                split_done = False
                for t_node in text_nodes:
                    t_text = t_node.text or ""
                    if sep in t_text:
                        t_parts = t_text.split(sep)
                        t_node.text = t_parts[0]
                        current_xml.append(elem)
                        options_xml.append(current_xml)
                        new_elem = copy.deepcopy(elem)
                        new_text_nodes = [t for t in new_elem.iter() if t.tag.endswith('}t')]
                        idx_of_node = text_nodes.index(t_node)
                        for k in range(idx_of_node):
                            new_text_nodes[k].text = ""
                        new_text_nodes[idx_of_node].text = t_parts[1]
                        current_xml = [new_elem]
                        split_done = True
                        break
                if not split_done:
                    current_xml.append(elem)
        else:
            current_xml.append(elem)
    if current_xml:
        options_xml.append(current_xml)
    return options_xml


def _count_math_formulas(questions):
    math_count = 0
    for q in questions:
        if 'question_xml' in q and q['question_xml']:
            for child in q['question_xml']:
                for node in child.iter():
                    if node.tag.endswith('}oMath'):
                        math_count += 1
        if 'options_xml' in q and q['options_xml']:
            for letter, opt_elements in q['options_xml']:
                for child in opt_elements:
                    for node in child.iter():
                        if node.tag.endswith('}oMath'):
                            math_count += 1
    return math_count

def _diagnose_error(err_msg: str) -> str:
    err_lower = err_msg.lower()
    if "permission denied" in err_lower or "errno 13" in err_lower:
        return (
            "🔒 **File Locked / Access Denied**:\n"
            "- The document is likely **open in Microsoft Word**. Please close Word and retry.\n"
            "- Alternatively, check if you have write permission for the destination directory."
        )
    elif "no such file" in err_lower or "errno 2" in err_lower:
        return (
            "🔍 **File Not Found**:\n"
            "- The source file might have been renamed, moved, or deleted after being added to the list.\n"
            "- Please verify the file path and reload the file."
        )
    elif "packagenotfounderror" in err_lower or "not a word file" in err_lower or "bad zip file" in err_lower:
        return (
            "📄 **Invalid Word Document Format**:\n"
            "- The file structure is corrupt or it is not a genuine OpenXML `.docx` file.\n"
            "- Note: Renamed old `.doc` binary documents are not supported; they must be saved as `.docx` in Word."
        )
    elif "xml" in err_lower or "element" in err_lower or "tag" in err_lower:
        return (
            "🧩 **XML/Structure Parsing Error**:\n"
            "- An unexpected structure or math formula formatting inside the document caused the parser to fail.\n"
            "- Try copying the text into a clean `.docx` file and retrying."
        )
    return (
        "❓ **Unknown Conversion Error**:\n"
        "- Ensure the file is not corrupted, not password-protected, and follows a recognizable MCQ format."
    )

# ---------------------------------------------------------------------------
# Enhanced Regex Patterns (More flexible input detection)
# ---------------------------------------------------------------------------

# Support BOM and multiple prefixes. Escaped unicode avoids non-ASCII characters.
# Handles Q1., Q:1., Question 1:, 1), various localized numbering variants, and Q: (no number).
QUESTION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:'
    r'(?:Q:?\s*|Question\s+)(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]*\s*(.*)' # Branch 1: Q/Question prefix + number (separator/body optional)
    r'|'
    r'(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\u9898]+\s*(.*)'                         # Branch 2: number + separator (prefix optional, separator required)
    r'|'
    r'(?:Q|Question)[:\uFF1A\s]\s*(.*)'                                         # Branch 3: Q/Question prefix + colon/space (no number)
    r')',
    re.IGNORECASE | re.DOTALL
)

# Support localized full-width letters, separators, and colon separators (e.g. A: Paris)
OPTION_RE = re.compile(r'^(?:[\ufeff\s]*)(?:\(|\[|\u3010|\uFF08)?([A-Ha-h])(?:[\)\.\uFF0E\u3001\]\u3011\s\uFF09:\uFF1A])+\s*(.*)', re.DOTALL)

# Support multiple answer prefixes including 'A' / 'A:' and localized variants
ANSWER_RE = re.compile(r'^(?:[\ufeff\s]*)(?:Answer|Ans|Key|A|\u6b63\u786e\u7b54\u6848|\u3010\u7b54\u6848\u3011|\u7b54\u6848)[:\uFF1A\s]\s*(.*)', re.IGNORECASE | re.DOTALL)

# Support optional Level information
LEVEL_RE = re.compile(r'^(?:[\ufeff\s]*)(?:Level)[:\uFF1A\s]+\s*(.*)', re.IGNORECASE | re.DOTALL)

# Regex to capture: Prefix, Number, Separator, Body for in-place renumbering
QUESTION_RE_INPLACE = re.compile(
    r'^([\ufeff\s]*(?:\u7b2c)?(?:Q:?|Question\s*)?)(\d+)([.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]+\s*)(.*)', 
    re.IGNORECASE | re.DOTALL
)

def renumber_docx_inplace(filepath: Path, output_path: Path):
    doc = Document(str(filepath))
    current_num = 1
    for para in doc.paragraphs:
        text = para.text
        m = QUESTION_RE_INPLACE.match(text)
        if m:
            prefix = m.group(1)
            old_num = m.group(2)
            sep = m.group(3)
            body = m.group(4)
            
            p_old = f"{prefix}{old_num}{sep}"
            p_new = f"{prefix}{current_num}{sep}"
            current_num += 1
            
            if para.runs:
                # Replace p_old with p_new in runs to preserve formatting
                remaining_len = len(p_old)
                first_run_modified = False
                
                for run in para.runs:
                    run_len = len(run.text)
                    if run_len == 0:
                        continue
                    
                    if not first_run_modified:
                        if run_len >= remaining_len:
                            run.text = p_new + run.text[remaining_len:]
                            remaining_len = 0
                        else:
                            run.text = p_new
                            remaining_len -= run_len
                        first_run_modified = True
                    else:
                        if remaining_len > 0:
                            if run_len >= remaining_len:
                                run.text = run.text[remaining_len:]
                                remaining_len = 0
                            else:
                                run.text = ""
                                remaining_len -= run_len
                        else:
                            break
            else:
                para.text = f"{prefix}{current_num}{sep}{body}"
    doc.save(str(output_path))

def _read_text_file(filepath: Path) -> List[str]:
    """Try reading a file with utf-8, fallback to system locale (e.g. gbk) if it fails."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.readlines()
    except UnicodeDecodeError:
        import locale
        sys_encoding = locale.getpreferredencoding()
        with open(filepath, 'r', encoding=sys_encoding, errors='replace') as f:
            return f.readlines()

def renumber_txt_inplace(filepath: Path, output_path: Path):
    lines = _read_text_file(filepath)
    
    new_lines = []
    current_num = 1
    for line in lines:
        m = QUESTION_RE_INPLACE.match(line)
        if m:
            prefix = m.group(1)
            sep = m.group(3)
            body = m.group(4)
            new_lines.append(f"{prefix}{current_num}{sep}{body}")
            current_num += 1
        else:
            new_lines.append(line)
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


def _parse_question(text: str) -> Optional[Tuple[Optional[int], str, int]]:
    text_stripped = text.strip()
    m = QUESTION_RE.match(text_stripped)
    if not m:
        return None
    if m.group(1) is not None:
        prefix_len = m.start(2)
        return int(m.group(1)), m.group(2).strip(), prefix_len
    elif m.group(3) is not None:
        prefix_len = m.start(4)
        return int(m.group(3)), m.group(4).strip(), prefix_len
    elif m.group(5) is not None:
        prefix_len = m.start(5)
        return None, m.group(5).strip(), prefix_len
    return None

def _parse_option(text: str) -> Optional[Tuple[str, str, int]]:
    text_stripped = text.strip()
    m = OPTION_RE.match(text_stripped)
    if not m:
        return None
    prefix_len = m.start(2)
    return m.group(1).upper(), m.group(2).strip(), prefix_len

def _parse_answer(text: str, current_options: Optional[List[str]] = None) -> Optional[str]:
    """
    Normalizes input answer into strict output format: "Answer: X) [Text]"
    If only 'A' is provided, it tries to find the text from current_options.
    """
    m = ANSWER_RE.match(text.strip())
    if not m:
        return None
    
    raw_ans = m.group(1).strip()
    
    # Check if raw_ans already contains 'X) Text' or just 'X'
    letter_match = re.match(r'^([A-H])(?:[\)\.\uFF0E\u3001\s]|$)\s*(.*)', raw_ans, re.IGNORECASE)
    if letter_match:
        letter = letter_match.group(1).upper()
        content = letter_match.group(2).strip()
        
        # If no content was after the letter, try to look it up in current_options
        if not content and current_options:
            for opt in current_options:
                if opt.startswith(f"{letter})"):
                    content = opt[len(letter)+2:].strip()
                    break
        
        return f"Answer: {letter}) {content}".strip()
    
    # If raw_ans doesn't start with a letter, try to match it against option text values
    if current_options:
        for opt in current_options:
            opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
            if opt_match:
                opt_letter = opt_match.group(1).upper()
                opt_text = opt_match.group(2).strip()
                if opt_text.lower() == raw_ans.lower():
                    return f"Answer: {opt_letter}) {opt_text}".strip()

    # Fallback: if it doesn't match a letter, just return as is with "Answer: " prefix
    return "Answer: " + raw_ans

def _parse_level(text: str) -> Optional[str]:
    m = LEVEL_RE.match(text.strip())
    if not m:
        return None
    return "Level: " + m.group(1).strip()


# ---------------------------------------------------------------------------
# Parsing Logic
# ---------------------------------------------------------------------------

def _paragraphs_to_questions(paragraphs, warnings_list=None):
    questions = []
    current = None

    def _save(q):
        if q is None:
            return
        if len(q['options']) < 2: # Lowered constraint for input flex, but warning remains
             w = f"Warning: Q{q['num'] or '?'} has only {len(q['options'])} options."
             print("  " + w)
             if warnings_list is not None:
                 warnings_list.append(w)
        if not q['answer']:
             w = f"Warning: Q{q['num'] or '?'} has no answer."
             print("  " + w)
             if warnings_list is not None:
                 warnings_list.append(w)
        questions.append(q)

    for item in paragraphs:
        if not item:
            continue

        if isinstance(item, str):
            text = item
            elements = [_create_run_xml(item)]
        else:
            text = _get_paragraph_text_with_math(item)
            elements = _get_para_xml_elements(item)

        text_stripped = text.strip()
        if not text_stripped:
            continue

        if (res := _parse_question(text_stripped)):
            _save(current)
            num, body, prefix_len = res
            
            # Clone and strip question prefix from XML elements
            q_elements = copy.deepcopy(elements)
            _strip_xml_prefix(q_elements, prefix_len)
            
            current = {
                'num': num,
                'question': body,
                'question_xml': q_elements,
                'options': [],
                'options_xml': [],
                'answer': '',
                'level': ''
            }

        elif current is not None:
            lower_text = text_stripped.lower()
            if lower_text.startswith('options:'):
                opts_part = text_stripped.split(':', 1)[1]
                # Find prefix length up to the first option
                prefix_len = text_stripped.index(opts_part)
                
                # Clone elements and strip "Options: " prefix
                opts_line_elements = copy.deepcopy(elements)
                _strip_xml_prefix(opts_line_elements, prefix_len)
                
                # Split options XML elements by separator "|"
                split_options_xml = _split_xml_elements_by_separator(opts_line_elements, "|")
                
                opts = [o.strip() for o in opts_part.split('|')]
                for idx, opt_str in enumerate(opts):
                    opt_str = opt_str.strip()
                    if idx < len(split_options_xml):
                        opt_elements = split_options_xml[idx]
                    else:
                        opt_elements = [_create_run_xml(opt_str)]
                        
                    if (res := _parse_option(opt_str)):
                        letter, body, opt_prefix_len = res
                        _strip_xml_prefix(opt_elements, opt_prefix_len)
                        current['options'].append(f"{letter}) {body}")
                        current['options_xml'].append((letter, opt_elements))
                    else:
                        # Auto-assign letter if no prefix exists
                        letter = chr(ord('A') + idx)
                        current['options'].append(f"{letter}) {opt_str}")
                        current['options_xml'].append((letter, opt_elements))
            elif current['options'] and (ans := _parse_answer(text_stripped, current['options'])):
                # Prioritize checking answer if we already have options parsed (e.g. A: Paris)
                current['answer'] = ans
            elif (res := _parse_option(text_stripped)):
                letter, body, prefix_len = res
                opt_elements = copy.deepcopy(elements)
                _strip_xml_prefix(opt_elements, prefix_len)
                current['options'].append(f"{letter}) {body}")
                current['options_xml'].append((letter, opt_elements))
            elif (ans := _parse_answer(text_stripped, current['options'])):
                # Pass current options to help rebuild full answer text if missing
                current['answer'] = ans
            elif (lvl := _parse_level(text_stripped)):
                current['level'] = lvl
            else:
                if not current['options']:
                    if current['question']:
                        current['question'] += "\n" + text_stripped
                        current['question_xml'].append(_create_br_xml())
                    else:
                        current['question'] = text_stripped
                    current['question_xml'].extend(copy.deepcopy(elements))

    _save(current)
    return questions


def _get_paragraph_text_with_math(para):
    """
    Extracts all text from a paragraph, including standard text runs 
    and Office Math (OMML) equation elements.
    """
    text_parts = []
    for elem in para._element.iter():
        if elem.tag.endswith('}t'):
            text_parts.append(elem.text or '')
    return "".join(text_parts)


def parse_docx(filepath: Path, warnings_list=None):
    doc = Document(str(filepath))
    return _paragraphs_to_questions(doc.paragraphs, warnings_list)


def parse_txt(filepath: Path, warnings_list=None):
    lines = [ln.rstrip('\n\r').strip() for ln in _read_text_file(filepath)]
    return _paragraphs_to_questions(lines, warnings_list)


# ---------------------------------------------------------------------------
# Output Logic (STRICTLY UNCHANGED - Following your required template)
# ---------------------------------------------------------------------------

def _build_options_line(options):
    """'Options: A) ... | B) ... | C) ... | D) ...'"""
    return "Options: " + " | ".join(options)


def renumber_questions(questions, start: int = 1):
    """Return a new list of questions with sequentially reassigned `num`.

    Preserves the original order but replaces `num` with consecutive
    integers starting at `start` (default 1). Does not modify the input
    list objects; returns shallow-copied dicts.
    """
    new = []
    for i, q in enumerate(questions, start=start):
        nq = q.copy()
        nq['num'] = i
        new.append(nq)
    return new


def _build_output_document(questions):
    """Create a python-docx Document using the new MCQ template."""
    from docx import Document

    # Ensure question numbers are sequential in the output
    questions = renumber_questions(questions, start=1)

    doc = Document()

    # Remove the single empty paragraph that Document() inserts by default.
    if doc.paragraphs and doc.paragraphs[0].text == '':
        p = doc.paragraphs[0]
        p._element.getparent().remove(p._element)

    try:
        normal = doc.styles['Normal']
    except KeyError:
        normal = None

    for i, q in enumerate(questions):
        # 1. Question text
        p_q = doc.add_paragraph(style=normal)
        p_q.add_run(f"{q['num']}. ")
        
        # Copy question XML elements
        if 'question_xml' in q and q['question_xml']:
            for child in q['question_xml']:
                p_q._element.append(copy.deepcopy(child))
        else:
            p_q.add_run(q['question'])

        # 2. Options
        if 'options_xml' in q and q['options_xml']:
            for letter, opt_elements in q['options_xml']:
                p_opt = doc.add_paragraph(style=normal)
                p_opt.add_run(f"{letter}. ")
                for child in opt_elements:
                    p_opt._element.append(copy.deepcopy(child))
        else:
            # Fallback
            for opt in q['options']:
                opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
                if opt_match:
                    letter = opt_match.group(1).upper()
                    body = opt_match.group(2)
                    doc.add_paragraph(f"{letter}. {body}", style=normal)
                else:
                    doc.add_paragraph(opt, style=normal)

        # Extract answer letter (e.g. 'A') from 'Answer: A) Opt1'
        ans_letter = ""
        if q['answer']:
            m = re.match(r'^Answer:\s*([A-H])(?:\)|\]|\.|\s|$)', q['answer'], re.IGNORECASE)
            if m:
                ans_letter = m.group(1).upper()
            else:
                # Fallback: search for an isolated A-H letter after 'Answer:'
                m2 = re.search(r'\b([A-H])\b', q['answer'].replace('Answer:', ''), re.IGNORECASE)
                if m2:
                    ans_letter = m2.group(1).upper()
        
        if ans_letter:
            doc.add_paragraph(f"Answer: {ans_letter}", style=normal)
        else:
            doc.add_paragraph(q['answer'], style=normal)

        # Blank separator line between questions (not after the last one)
        if i < len(questions) - 1:
            doc.add_paragraph('', style=normal)

    return doc


# ---------------------------------------------------------------------------
# GUI Application
# ---------------------------------------------------------------------------

class MCQConverterApp(TkinterDnDCTk):
    def __init__(self):
        super().__init__()

        self.title("MCQ Batch Converter Pro")
        self.geometry("960x600")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#F1F5F9") # Soft neutral background

        self.input_files: List[Path] = []
        self.setup_ui()
        self.setup_dnd()

    def setup_ui(self):
        # Split layout: Left Frame for MCQ Converter, Right Frame for Copilot Sidebar
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=20)
        
        self.right_frame = ctk.CTkFrame(self, width=380, corner_radius=15, fg_color="#FFFFFF", border_width=1, border_color="#E2E8F0")
        self.right_frame.pack(side="right", fill="both", expand=False, padx=(10, 20), pady=20)
        self.right_frame.pack_propagate(False)

        # ----------------- Left Frame Components -----------------
        self.header = ctk.CTkLabel(self.left_frame, text="MCQ Converter", font=("Segoe UI", 26, "bold"), text_color="#1E293B")
        self.header.pack(pady=(10, 5))

        self.subheader = ctk.CTkLabel(self.left_frame, text="Advanced Batch Processing (Supports formulas)", font=("Segoe UI", 13), text_color="#64748B")
        self.subheader.pack(pady=(0, 10))

        # Drop Zone
        self.drop_frame = ctk.CTkFrame(self.left_frame, width=500, height=180, border_width=2, border_color="#3B82F6", fg_color="#F8FAFC", corner_radius=12)
        self.drop_frame.pack_propagate(False)
        self.drop_frame.pack(pady=10, padx=10)

        self.drop_label = ctk.CTkLabel(self.drop_frame, text="Drag and Drop files here\nor\nClick to Browse", 
                                      font=("Segoe UI", 15), text_color="#3B82F6", cursor="hand2")
        self.drop_label.pack(expand=True, fill="both")
        self.drop_label.bind("<Button-1>", lambda e: self.choose_files())

        # Selected Files Info
        self.file_info_var = ctk.StringVar(value="No files selected")
        self.file_info_label = ctk.CTkLabel(self.left_frame, textvariable=self.file_info_var, font=("Segoe UI", 11, "italic"), wraplength=480)
        self.file_info_label.pack(pady=5)

        # Mode Selection
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

        # Action Buttons
        self.button_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.button_frame.pack(pady=15)

        self.convert_btn = ctk.CTkButton(self.button_frame, text="Convert All", command=self.start_conversion, state="disabled", 
                                         fg_color="#F97316", hover_color="#EA580C", text_color="white", font=("Segoe UI", 15, "bold"), corner_radius=8)
        self.convert_btn.pack(side="left", padx=10)

        self.clear_btn = ctk.CTkButton(self.button_frame, text="Clear List", fg_color="transparent", hover_color="#F1F5F9", 
                                       border_width=1, border_color="#CBD5E1", text_color="#64748B", command=self.clear_selection, corner_radius=8)
        self.clear_btn.pack(side="left", padx=10)

        # Status
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(self.left_frame, textvariable=self.status_var, font=("Segoe UI", 13, "bold"), text_color="#2563EB")
        self.status_label.pack(side="bottom", pady=10)

        # ----------------- Right Frame Components (Copilot Sidebar) -----------------
        self.setup_copilot_sidebar()

    def setup_copilot_sidebar(self):
        # Header (Copilot Title Bar)
        self.copilot_title_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.copilot_title_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        self.copilot_title = ctk.CTkLabel(self.copilot_title_frame, text="Copilot", font=("Segoe UI", 18, "bold"), text_color="#1E293B")
        self.copilot_title.pack(side="left")
        
        # Green online dot
        self.online_dot = ctk.CTkLabel(self.copilot_title_frame, text="●", text_color="#10B981", font=("Segoe UI", 10))
        self.online_dot.pack(side="left", padx=(5, 0))
        
        self.copilot_subtitle = ctk.CTkLabel(self.right_frame, text="AI assistant powered by CopilotKit", font=("Segoe UI", 11, "italic"), text_color="#64748B")
        self.copilot_subtitle.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Scrollable Chat Log container
        self.chat_scroll_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.chat_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Chat Input Box and Send Button Panel
        self.chat_input_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
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

    def add_chat_message(self, sender: str, text: str, animate: bool = False, actions: list = None):
        # Create row frame
        row_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=6, padx=8)
        
        # Clean text (remove leftover markdown if any)
        clean_text = text.replace("**", "").replace("__", "")
        
        is_user = (sender.lower() == "user")
        bubble_color = "#E2E8F0" if is_user else "#3B82F6"
        text_color = "#1E293B" if is_user else "white"
        anchor_side = "right" if is_user else "left"
        anchor_align = "e" if is_user else "w"
        
        bubble = ctk.CTkFrame(row_frame, fg_color=bubble_color, corner_radius=12)
        bubble.pack(side=anchor_side, anchor=anchor_align)
        
        label = ctk.CTkLabel(bubble, text="" if animate else clean_text, text_color=text_color, font=("Segoe UI", 13),
                             wraplength=220, justify="left")
        label.pack(padx=12, pady=8)

        if actions and not is_user:
            actions_frame = ctk.CTkFrame(bubble, fg_color="transparent")
            actions_frame.pack(fill="x", padx=12, pady=(0, 8))
            for act in actions:
                btn = ctk.CTkButton(actions_frame, text=act["text"], height=24, font=("Segoe UI", 11, "bold"),
                                    fg_color="#FFFFFF", text_color="#3B82F6", hover_color="#F1F5F9",
                                    corner_radius=6, command=act["command"])
                btn.pack(side="left", padx=(0, 5), pady=2)
                
        if animate:
            self._animate_text(label, clean_text, 0)
            
        # Auto-scroll to bottom
        self.after(50, lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0))

    def _animate_text(self, label, full_text, index):
        if index <= len(full_text):
            label.configure(text=full_text[:index])
            self.chat_scroll_frame._parent_canvas.yview_moveto(1.0)
            self.after(15, self._animate_text, label, full_text, index + 1)

    def show_thinking_indicator(self):
        self.thinking_frame = ctk.CTkFrame(self.chat_scroll_frame, fg_color="transparent")
        self.thinking_frame.pack(fill="x", pady=6, padx=8)
        bubble = ctk.CTkFrame(self.thinking_frame, fg_color="#3B82F6", corner_radius=12)
        bubble.pack(side="left", anchor="w")
        self.thinking_label = ctk.CTkLabel(bubble, text="Thinking...", text_color="white", font=("Segoe UI", 13, "italic"))
        self.thinking_label.pack(padx=12, pady=8)
        self.after(50, lambda: self.chat_scroll_frame._parent_canvas.yview_moveto(1.0))
        self._animate_thinking(0)
        
    def _animate_thinking(self, dots):
        if hasattr(self, 'thinking_label') and self.thinking_label.winfo_exists():
            self.thinking_label.configure(text="Thinking" + "." * (dots % 4))
            self.after(400, self._animate_thinking, dots + 1)

    def hide_thinking_indicator(self):
        if hasattr(self, 'thinking_frame') and self.thinking_frame.winfo_exists():
            self.thinking_frame.destroy()

    def handle_chat_submit(self):
        msg = self.chat_entry.get().strip()
        if not msg:
            return
            
        self.chat_entry.delete(0, "end")
        self.add_chat_message("User", msg)
        self.show_thinking_indicator()
        
        self.chat_send_btn.configure(state="disabled")
        self.chat_entry.configure(state="disabled")
        
        threading.Thread(target=self.generate_copilot_reply, args=(msg,), daemon=True).start()

    def generate_copilot_reply(self, msg: str):
        import time
        
        msg_lower = msg.lower()
        
        # Check if setting API key
        if msg.startswith("/apikey "):
            key_part = msg[len("/apikey "):].strip()
            if _save_config_value("API_KEY", key_part):
                self.after(0, lambda: self.finish_copilot_reply("🔑 API Key saved successfully!"))
            else:
                self.after(0, lambda: self.finish_copilot_reply("❌ Failed to save API Key locally in config.json. Please check file permissions."))
            return
            
        # Check if setting base url
        if msg.startswith("/baseurl "):
            url_part = msg[len("/baseurl "):].strip()
            if _save_config_value("BASE_URL", url_part):
                self.after(0, lambda: self.finish_copilot_reply(f"🔗 Base URL saved successfully!\n{url_part}"))
            else:
                self.after(0, lambda: self.finish_copilot_reply("❌ Failed to save Base URL settings."))
            return
            
        # Check if setting model name
        if msg.startswith("/model "):
            model_part = msg[len("/model "):].strip()
            if _save_config_value("MODEL", model_part):
                self.after(0, lambda: self.finish_copilot_reply(f"🎯 Model name saved successfully!\n{model_part}"))
            else:
                self.after(0, lambda: self.finish_copilot_reply("❌ Failed to save model name settings."))
            return

        # Get active config
        config = _get_config()
        api_key = config.get("API_KEY")
        
        # Check command: clear
        if "clear" in msg_lower:
            self.after(0, lambda: self.clear_selection(notify=False))
            response = "🧹 File list cleared! You can now drag and drop new files."
            self.after(0, lambda r=response: self.finish_copilot_reply(r))
            
        # Check command: renumber
        elif "renumber" in msg_lower:
            self.after(0, lambda: self.mode_var.set("renumber"))
            response = "🔄 Switched conversion mode to: Only Renumber."
            self.after(0, lambda r=response: self.finish_copilot_reply(r))
            
        # Check command: standard
        elif "standard" in msg_lower:
            self.after(0, lambda: self.mode_var.set("standard"))
            response = "📋 Switched conversion mode to: Standardize Format."
            self.after(0, lambda r=response: self.finish_copilot_reply(r))
            
        # Check command: convert
        elif "convert" in msg_lower:
            if not self.input_files:
                response = "⚠️ You haven't selected any files yet! Please drag and drop or browse files first, then ask me to convert."
            else:
                response = f"🚀 Starting conversion for {len(self.input_files)} file(s) right now..."
                self.after(0, self.start_conversion)
            self.after(0, lambda r=response: self.finish_copilot_reply(r))
            
        # Check command: help
        elif "help" in msg_lower:
            response = (
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
                "- /apikey <key>: Set API Key.\n"
                "- /baseurl <url>: Set custom API base URL.\n"
                "- /model <name>: Set model name."
            )
            self.after(500, lambda r=response: self.finish_copilot_reply(r))
            
        # If no API key is set, and it's not a command, prompt user to set it
        elif not api_key:
            response = (
                "⚠️ API Key not found.\n\n"
                "To enable the AI model for Q&A, please type '/apikey <your_key>' in this chat box to save it locally in config.json.\n\n"
                "(Basic local commands like clear, convert, standard, renumber, and help are still available without a key!)"
            )
            self.after(500, lambda r=response: self.finish_copilot_reply(r))
            
        # Otherwise, call LLM API!
        else:
            context = ""
            if self.input_files:
                file_names = ", ".join(f.name for f in self.input_files)
                context = f"[Context: The user has loaded these files into the MCQ Converter: {file_names}]\n"
            
            prompt = f"{context}User message: {msg}"
            response = call_llm_api(prompt, config)
            self.after(0, lambda r=response: self.finish_copilot_reply(r))

    def finish_copilot_reply(self, reply_text, actions=None):
        self.hide_thinking_indicator()
        self.add_chat_message("Copilot", reply_text, animate=True, actions=actions)
        self.chat_send_btn.configure(state="normal")
        self.chat_entry.configure(state="normal")
        self.chat_entry.focus()

    def setup_dnd(self):
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)

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
        
        # Notify Copilot of added files
        mode = self.mode_var.get()
        mode_str = "Standardize Format" if mode == "standard" else "Only Renumber"
        added_list = ", ".join(f"{p.name}" for p in paths)
        
        msg = f"📂 Added to conversion queue:\n- {added_list}\n\n(Ready to process in {mode_str} mode)"
        actions = [
            {"text": "🚀 Convert Now", "command": self.start_conversion},
            {"text": "🧹 Clear", "command": lambda: self.clear_selection(notify=True)}
        ]
        self.add_chat_message("Copilot", msg, animate=True, actions=actions)

    def clear_selection(self, notify=True):
        self.input_files = []
        self.file_info_var.set("No files selected")
        self.status_var.set("Ready")
        self.convert_btn.configure(state="disabled")
        self.drop_frame.configure(border_color="#1f538d")
        if notify:
            self.add_chat_message("Copilot", "🧹 File queue cleared.", animate=True)

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
        
        # Notify Copilot that conversion has started
        mode = self.mode_var.get()
        mode_str = "Standardize Format" if mode == "standard" else "Only Renumber"
        file_list = ", ".join(f"{f.name}" for f, _ in targets)
        self.add_chat_message("Copilot", f"🚀 Starting conversion for:\n- {file_list}\n\n(Mode: {mode_str})", animate=True)
        
        threading.Thread(target=self.process_batch, args=(targets,), daemon=True).start()

    def process_batch(self, targets: List[Tuple[Path, Path]]):
        success_count = 0
        total = len(targets)
        failed_files = []
        mode = self.mode_var.get()
        batch_details = []
        
        for i, (inp, out) in enumerate(targets):
            self.after(0, lambda idx=i+1, name=inp.name: self.status_var.set(f"Processing ({idx}/{total}): {name}"))
            try:
                ext = inp.suffix.lower()
                math_count = 0
                warnings_list = []
                if mode == "renumber":
                    if ext == '.docx':
                        renumber_docx_inplace(inp, out)
                        try:
                            doc = Document(str(out))
                            math_count = sum(1 for p in doc.paragraphs if any(c.tag.endswith('}oMath') for c in p._element.iter()))
                        except Exception:
                            pass
                    else:
                        renumber_txt_inplace(inp, out)
                    success_count += 1
                else:
                    questions = parse_docx(inp, warnings_list) if ext == '.docx' else parse_txt(inp, warnings_list)
                    if questions:
                        math_count = _count_math_formulas(questions)
                        _build_output_document(questions).save(str(out))
                        success_count += 1
                        
                        # Notify Copilot of warnings
                        if warnings_list:
                            self.after(0, lambda name=inp.name, w=warnings_list: self.notify_warnings_in_chat(name, w))
                
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

        if failed_files:
            err_msg = "\n".join([f"{name}: {err}" for name, err in failed_files[:5]])
            if len(failed_files) > 5:
                err_msg += f"\n... and {len(failed_files)-5} more."
            self.after(0, lambda msg=err_msg: self.show_error(f"Some files failed:\n{msg}"))

        self.after(0, lambda: self.finish_batch(success_count, total, batch_details))

    def show_error(self, msg):
        messagebox.showerror("Failed", msg)
        self.status_var.set("An error occurred.")
        self.convert_btn.configure(state="normal")
        self.clear_btn.configure(state="normal")

    def finish_batch(self, success, total, batch_details):
        self.status_var.set(f"Done! {success}/{total} files converted.")
        messagebox.showinfo("Success", f"Successfully converted {success} of {total} files.")
        
        # Detailed success notification in Copilot Chat Sidebar
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
                
        self.add_chat_message("Copilot", "\n".join(msg_parts), animate=True)
        
        self.clear_selection(notify=False)
        self.clear_btn.configure(state="normal")

    def notify_warnings_in_chat(self, filename: str, warnings: List[str]):
        warn_msg = f"⚠️ I detected some formatting issues in {filename} during conversion:\n\n"
        for w in warnings:
            cleaned_w = w.replace("Warning: ", "")
            warn_msg += f"- {cleaned_w}\n"
        warn_msg += "\nTip: Check the source document to make sure questions have at least 2 options and a valid Answer."
        self.add_chat_message("Copilot", warn_msg, animate=True)

    def notify_error_in_chat(self, filename: str, err_msg: str):
        diagnostic = _diagnose_error(err_msg)
        # remove markdown from diagnostic message
        diagnostic_clean = diagnostic.replace("**", "")
        err_text = (
            f"❌ Failed to convert {filename}\n\n"
            f"Error Details: {err_msg}\n\n"
            f"Diagnosis & Actionable Advice:\n{diagnostic_clean}"
        )
        self.add_chat_message("Copilot", err_text, animate=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ['--gui', '-g']:
        app = MCQConverterApp()
        app.mainloop()
    else:
        only_renumber = False
        if '--only-renumber' in args:
            only_renumber = True
            args.remove('--only-renumber')
        if '-r' in args:
            only_renumber = True
            args.remove('-r')
            
        if len(args) < 1:
            print("Usage: python convert_mcq.py <input_file> [<output_file>] [--only-renumber]", file=sys.stderr)
            sys.exit(1)
            
        inp = Path(args[0])
        out = Path(args[1]) if len(args) > 1 else inp.with_name(inp.stem + "_MCQ.docx")
        
        try:
            if only_renumber:
                if inp.suffix.lower() == '.docx':
                    renumber_docx_inplace(inp, out)
                else:
                    renumber_txt_inplace(inp, out)
                print(f"Success: Renumbered '{inp.name}' -> '{out.name}'")
            else:
                questions = parse_docx(inp) if inp.suffix.lower() == '.docx' else parse_txt(inp)
                if questions:
                    _build_output_document(questions).save(str(out))
                    print(f"Success: Converted '{inp.name}' -> '{out.name}'")
                else:
                    print("No questions found or failed to parse input.", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
