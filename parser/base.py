import re
import copy
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------
QUESTION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:'
    r'(?:Q:?\s*|Question\s+)(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]*\s*(.*)'
    r'|'
    r'(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\u9898]+\s*(.*)'
    r'|'
    r'(?:Q|Question)[:\uFF1A\s]\s*(.*)'
    r')',
    re.IGNORECASE | re.DOTALL
)

OPTION_RE = re.compile(r'^(?:[\ufeff\s]*)(?:\(|\[|\u3010|\uFF08)?([A-Ha-h])(?:[\)\.\uFF0E\u3001\]\u3011\s\uFF09:\uFF1A])+\s*(.*)', re.DOTALL)
ANSWER_RE = re.compile(r'^(?:[\ufeff\s]*)(?:Answer|Ans|Key|A|\u6b63\u786e\u7b54\u6848|\u3010\u7b54\u6848\u3011|\u7b54\u6848)[:\uFF1A\s]\s*(.*)', re.IGNORECASE | re.DOTALL)
LEVEL_RE = re.compile(r'^(?:[\ufeff\s]*)(?:Level)[:\uFF1A\s]+\s*(.*)', re.IGNORECASE | re.DOTALL)
QUESTION_RE_INPLACE = re.compile(
    r'^([\ufeff\s]*(?:\u7b2c)?(?:Q:?|Question\s*)?)(\d+)([.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]+\s*)(.*)', 
    re.IGNORECASE | re.DOTALL
)

# ---------------------------------------------------------------------------
# XML & Math Utilities
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

def count_math_formulas(questions):
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

def diagnose_error(err_msg: str) -> str:
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

def _get_paragraph_text_with_math(para):
    text_parts = []
    for elem in para._element.iter():
        if elem.tag.endswith('}t'):
            text_parts.append(elem.text or '')
    return "".join(text_parts)

def _read_text_file(filepath: Path) -> List[str]:
    encodings = ['utf-8', 'gb18030', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.readlines()
        except (UnicodeDecodeError, LookupError):
            continue
            
    import locale
    sys_encoding = locale.getpreferredencoding()
    try:
        with open(filepath, 'r', encoding=sys_encoding, errors='replace') as f:
            return f.readlines()
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Individual Subroutines
# ---------------------------------------------------------------------------
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
    m = ANSWER_RE.match(text.strip())
    if not m:
        return None
    
    raw_ans = m.group(1).strip()
    letter_match = re.match(r'^([A-H])(?:[\)\.\uFF0E\u3001\s]|$)\s*(.*)', raw_ans, re.IGNORECASE)
    if letter_match:
        letter = letter_match.group(1).upper()
        content = letter_match.group(2).strip()
        
        if not content and current_options:
            for opt in current_options:
                if opt.startswith(f"{letter})"):
                    content = opt[len(letter)+2:].strip()
                    break
        return f"Answer: {letter}) {content}".strip()
    
    if current_options:
        for opt in current_options:
            opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
            if opt_match:
                opt_letter = opt_match.group(1).upper()
                opt_text = opt_match.group(2).strip()
                if opt_text.lower() == raw_ans.lower():
                    return f"Answer: {opt_letter}) {opt_text}".strip()

    return "Answer: " + raw_ans

def _parse_level(text: str) -> Optional[str]:
    m = LEVEL_RE.match(text.strip())
    if not m:
        return None
    return "Level: " + m.group(1).strip()

def _paragraphs_to_questions(paragraphs, warnings_list=None):
    questions = []
    current = None

    def _save(q):
        if q is None:
            return
        if len(q['options']) < 2:
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
                prefix_len = text_stripped.index(opts_part)
                
                opts_line_elements = copy.deepcopy(elements)
                _strip_xml_prefix(opts_line_elements, prefix_len)
                
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
                        letter = chr(ord('A') + idx)
                        current['options'].append(f"{letter}) {opt_str}")
                        current['options_xml'].append((letter, opt_elements))
            elif current['options'] and (ans := _parse_answer(text_stripped, current['options'])):
                current['answer'] = ans
            elif (res := _parse_option(text_stripped)):
                letter, body, prefix_len = res
                opt_elements = copy.deepcopy(elements)
                _strip_xml_prefix(opt_elements, prefix_len)
                current['options'].append(f"{letter}) {body}")
                current['options_xml'].append((letter, opt_elements))
            elif (ans := _parse_answer(text_stripped, current['options'])):
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
