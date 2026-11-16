import re
import copy
import unicodedata
from typing import Optional, Tuple, List

from parser.models import Question
from parser.regex import (
    QUESTION_RE, OPTION_RE, INLINE_OPTION_SPLIT_RE,
    ANSWER_RE, LEVEL_RE, EXPLANATION_RE
)
from parser.xml_utils import (
    create_run_xml, create_br_xml,
    get_para_xml_elements, strip_xml_prefix,
    split_xml_elements_by_separator, get_paragraph_text_with_math
)
from logger import get_logger

logger = get_logger()

_INLINE_OPTIONS_PREFIX_RE = re.compile(r'^(?:options|\u9009\u9879)[:\uFF1A]\s*(.*)', re.IGNORECASE | re.DOTALL)
_MULTI_LETTER_SEP_RE = re.compile(r'^[A-H](?:[\s,\u3001/;+&|]+[A-H])+$', re.IGNORECASE)
_MULTI_LETTER_COMPACT_RE = re.compile(r'^[A-H]{2,8}$', re.IGNORECASE)


def diagnose_error(err_msg: str) -> str:
    err_lower = err_msg.lower()
    if "permission denied" in err_lower or "errno 13" in err_lower:
        return (
            "File Locked / Access Denied:\n"
            "- The document is likely open in Microsoft Word. Please close Word and retry.\n"
            "- Alternatively, check if you have write permission for the destination directory."
        )
    if "no such file" in err_lower or "errno 2" in err_lower:
        return (
            "File Not Found:\n"
            "- The source file might have been renamed, moved, or deleted after being added to the list.\n"
            "- Please verify the file path and reload the file."
        )
    if "packagenotfounderror" in err_lower or "not a word file" in err_lower or "bad zip file" in err_lower:
        return (
            "Invalid Word Document Format:\n"
            "- The file structure is corrupt or it is not a genuine OpenXML .docx file.\n"
            "- Note: Renamed old .doc binary documents are not supported; they must be saved as .docx in Word."
        )
    if "xml" in err_lower or "element" in err_lower or "tag" in err_lower:
        return (
            "XML/Structure Parsing Error:\n"
            "- An unexpected structure or math formula formatting inside the document caused the parser to fail.\n"
            "- Try copying the text into a clean .docx file and retrying."
        )
    return (
        "Unknown Conversion Error:\n"
        "- Ensure the file is not corrupted, not password-protected, and follows a recognizable MCQ format."
    )


def raw_prefix_length(raw_text: str, nfkc_prefix_len: int) -> int:
    leading_ws = len(raw_text) - len(raw_text.lstrip())
    stripped = raw_text.lstrip()
    if nfkc_prefix_len <= 0:
        return leading_ws
    nfkc_count = 0
    for idx, ch in enumerate(stripped):
        if nfkc_count >= nfkc_prefix_len:
            return leading_ws + idx
        nfkc_count += len(unicodedata.normalize('NFKC', ch))
    return leading_ws + len(stripped)


def parse_question(text: str) -> Optional[Tuple[Optional[int], str, int]]:
    text_stripped = unicodedata.normalize('NFKC', text.strip())
    m = QUESTION_RE.match(text_stripped)
    if not m:
        return None
    for num_idx, body_idx in ((1, 2), (3, 4), (5, 6)):
        if m.group(num_idx) is not None:
            return int(m.group(num_idx)), m.group(body_idx).strip(), m.start(body_idx)
    if m.group(7) is not None:
        return None, m.group(7).strip(), m.start(7)
    return None


def parse_option(text: str) -> Optional[Tuple[str, str, int]]:
    text_stripped = unicodedata.normalize('NFKC', text.strip())
    m = OPTION_RE.match(text_stripped)
    if not m:
        return None
    if m.group(1) is not None:
        return m.group(1).upper(), m.group(2).strip(), m.start(2)
    return m.group(3).upper(), m.group(4).strip(), m.start(4)


def _dedupe_letters(letters: List[str]) -> List[str]:
    seen = set()
    result = []
    for letter in letters:
        up = letter.upper()
        if up not in seen:
            seen.add(up)
            result.append(up)
    return result


def extract_answer_letters(answer_text: str) -> List[str]:
    if not answer_text:
        return []
    cleaned = unicodedata.normalize('NFKC', answer_text).strip()
    cleaned = re.sub(
        r'^(?:Answer|Ans|Key|\u7b54\u6848|\u6b63\u786e\u7b54\u6848)\s*[:\uFF1A]?\s*',
        '',
        cleaned,
        flags=re.IGNORECASE,
    )

    if _MULTI_LETTER_SEP_RE.match(cleaned) or _MULTI_LETTER_COMPACT_RE.match(cleaned):
        return _dedupe_letters(re.findall(r'[A-H]', cleaned, re.IGNORECASE))

    single_m = re.match(r'^([A-H])(?:\)|\]|\.|\s|$)', cleaned, re.IGNORECASE)
    if single_m:
        return [single_m.group(1).upper()]

    return []


def parse_answer(text: str, current_options: Optional[List[str]] = None) -> Optional[str]:
    text_stripped = unicodedata.normalize('NFKC', text.strip())
    m = ANSWER_RE.match(text_stripped)
    if not m:
        return None

    raw_ans = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
    if not raw_ans:
        return None

    if _MULTI_LETTER_SEP_RE.match(raw_ans) or _MULTI_LETTER_COMPACT_RE.match(raw_ans):
        all_letters = _dedupe_letters(re.findall(r'[A-H]', raw_ans, re.IGNORECASE))
        if len(all_letters) > 1:
            return f"Answer: {', '.join(all_letters)}"

    letter_match = re.match(r'^([A-H])(?:[\)\.\uFF0E\u3001\s]|$)\s*(.*)', raw_ans, re.IGNORECASE)
    if letter_match:
        letter = letter_match.group(1).upper()
        content = letter_match.group(2).strip()
        if not content and current_options:
            for opt in current_options:
                if opt.startswith(f"{letter})"):
                    content = opt[len(letter) + 2:].strip()
                    break
        return f"Answer: {letter}) {content}".strip()

    if current_options:
        for opt in current_options:
            opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
            if opt_match and opt_match.group(2).strip().lower() == raw_ans.lower():
                return f"Answer: {opt_match.group(1).upper()}) {opt_match.group(2).strip()}".strip()

    return "Answer: " + raw_ans


def parse_level(text: str) -> Optional[str]:
    text_stripped = unicodedata.normalize('NFKC', text.strip())
    m = LEVEL_RE.match(text_stripped)
    if not m:
        return None
    return "Level: " + m.group(1).strip()


def parse_explanation(text: str) -> Optional[Tuple[str, int]]:
    text_stripped = unicodedata.normalize('NFKC', text.strip())
    m = EXPLANATION_RE.match(text_stripped)
    if not m:
        return None
    return m.group(1).strip(), m.start(1)


def _try_split_inline_options(text_stripped: str) -> Optional[List[Tuple[str, str]]]:
    parts = [p.strip() for p in INLINE_OPTION_SPLIT_RE.split(text_stripped) if p.strip()]
    if len(parts) < 2:
        return None
    parsed = []
    for part in parts:
        opt_res = parse_option(part)
        if not opt_res:
            return None
        parsed.append((opt_res[0], opt_res[1]))
    return parsed


def _handle_options_prefix(current: Question, text: str, text_stripped: str, elements: list) -> bool:
    nfkc_stripped = unicodedata.normalize('NFKC', text_stripped)
    m = _INLINE_OPTIONS_PREFIX_RE.match(nfkc_stripped)
    if not m:
        return False

    opts_part = m.group(1)
    nfkc_prefix_len = m.start(1)
    opts_line_elements = copy.deepcopy(elements)
    strip_xml_prefix(opts_line_elements, raw_prefix_length(text, nfkc_prefix_len))

    split_options_xml = split_xml_elements_by_separator(opts_line_elements, "|")
    opts = [o.strip() for o in opts_part.split('|')]
    for idx, opt_str in enumerate(opts):
        if not opt_str:
            continue
        opt_elements = split_options_xml[idx] if idx < len(split_options_xml) else [create_run_xml(opt_str)]
        opt_result = parse_option(opt_str)
        if opt_result:
            letter, body, opt_prefix_len = opt_result
            strip_xml_prefix(opt_elements, raw_prefix_length(opt_str, opt_prefix_len))
            current.options.append(f"{letter}) {body}")
            current.options_xml.append((letter, opt_elements))
        else:
            letter = chr(ord('A') + len(current.options))
            current.options.append(f"{letter}) {opt_str}")
            current.options_xml.append((letter, opt_elements))
    return True


def _apply_answer(current: Question, ans: str) -> None:
    current.answer = ans
    if len(extract_answer_letters(ans)) > 1:
        current.q_type = "multiple"


def _append_continuation(current: Question, last_section: str, text_stripped: str, elements: list) -> None:
    if last_section == "question":
        if current.question:
            current.question += "\n" + text_stripped
            current.question_xml.append(create_br_xml())
        else:
            current.question = text_stripped
        current.question_xml.extend(copy.deepcopy(elements))
    elif last_section == "option" and current.options:
        current.options[-1] += "\n" + text_stripped
        if current.options_xml:
            current.options_xml[-1][1].append(create_br_xml())
            current.options_xml[-1][1].extend(copy.deepcopy(elements))
    elif last_section == "explanation":
        if current.explanation:
            current.explanation += "\n" + text_stripped
            current.explanation_xml.append(create_br_xml())
        else:
            current.explanation = text_stripped
        current.explanation_xml.extend(copy.deepcopy(elements))


def _save_question(q: Optional[Question], questions: list, warnings_list: Optional[list]) -> None:
    if q is None:
        return
    if len(q.options) < 2:
        w = f"Warning: Q{q.num or '?'} has only {len(q.options)} options."
        logger.warning(w)
        if warnings_list is not None:
            warnings_list.append(w)
    if not q.answer:
        w = f"Warning: Q{q.num or '?'} has no answer."
        logger.warning(w)
        if warnings_list is not None:
            warnings_list.append(w)
    questions.append(q)


def paragraphs_to_questions(paragraphs, warnings_list=None):
    questions: List[Question] = []
    current: Optional[Question] = None
    last_section = "question"

    for item in paragraphs:
        if not item:
            continue

        if isinstance(item, str):
            text = item
            elements = [create_run_xml(item)]
        else:
            text = get_paragraph_text_with_math(item)
            elements = get_para_xml_elements(item)

        text_stripped = text.strip()
        if not text_stripped:
            continue

        result = parse_question(text_stripped)
        if result:
            _save_question(current, questions, warnings_list)
            num, body, nfkc_prefix_len = result
            q_elements = copy.deepcopy(elements)
            strip_xml_prefix(q_elements, raw_prefix_length(text, nfkc_prefix_len))
            current = Question(num=num, question=body, question_xml=q_elements)
            last_section = "question"
            continue

        if current is None:
            continue

        if _handle_options_prefix(current, text, text_stripped, elements):
            last_section = "option"
        elif current.options and (ans := parse_answer(text_stripped, current.options)):
            _apply_answer(current, ans)
            last_section = "answer"
        elif (inline_opts := _try_split_inline_options(text_stripped)):
            for letter, body in inline_opts:
                current.options.append(f"{letter}) {body}")
                current.options_xml.append((letter, [create_run_xml(body)]))
            last_section = "option"
        elif (opt_result := parse_option(text_stripped)):
            letter, body, nfkc_prefix_len = opt_result
            opt_elements = copy.deepcopy(elements)
            strip_xml_prefix(opt_elements, raw_prefix_length(text, nfkc_prefix_len))
            current.options.append(f"{letter}) {body}")
            current.options_xml.append((letter, opt_elements))
            last_section = "option"
        elif (ans := parse_answer(text_stripped, current.options)):
            _apply_answer(current, ans)
            last_section = "answer"
        elif (lvl := parse_level(text_stripped)):
            current.level = lvl
            last_section = "level"
        elif (exp_result := parse_explanation(text_stripped)):
            exp_body, nfkc_prefix_len = exp_result
            exp_elements = copy.deepcopy(elements)
            strip_xml_prefix(exp_elements, raw_prefix_length(text, nfkc_prefix_len))
            current.explanation = exp_body
            current.explanation_xml = exp_elements
            last_section = "explanation"
        else:
            _append_continuation(current, last_section, text_stripped, elements)

    _save_question(current, questions, warnings_list)
    return questions


