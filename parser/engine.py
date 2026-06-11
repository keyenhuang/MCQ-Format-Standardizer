import re
import copy
from typing import Optional, Tuple, List

from parser.models import Question
from parser.regex import QUESTION_RE, OPTION_RE, ANSWER_RE, LEVEL_RE
from parser.xml_utils import (
    create_run_xml, create_br_xml,
    get_para_xml_elements, strip_xml_prefix,
    split_xml_elements_by_separator, get_paragraph_text_with_math
)
from logger import get_logger

logger = get_logger()


def diagnose_error(err_msg: str) -> str:
    err_lower = err_msg.lower()
    if "permission denied" in err_lower or "errno 13" in err_lower:
        return (
            "File Locked / Access Denied:\n"
            "- The document is likely open in Microsoft Word. Please close Word and retry.\n"
            "- Alternatively, check if you have write permission for the destination directory."
        )
    elif "no such file" in err_lower or "errno 2" in err_lower:
        return (
            "File Not Found:\n"
            "- The source file might have been renamed, moved, or deleted after being added to the list.\n"
            "- Please verify the file path and reload the file."
        )
    elif "packagenotfounderror" in err_lower or "not a word file" in err_lower or "bad zip file" in err_lower:
        return (
            "Invalid Word Document Format:\n"
            "- The file structure is corrupt or it is not a genuine OpenXML .docx file.\n"
            "- Note: Renamed old .doc binary documents are not supported; they must be saved as .docx in Word."
        )
    elif "xml" in err_lower or "element" in err_lower or "tag" in err_lower:
        return (
            "XML/Structure Parsing Error:\n"
            "- An unexpected structure or math formula formatting inside the document caused the parser to fail.\n"
            "- Try copying the text into a clean .docx file and retrying."
        )
    return (
        "Unknown Conversion Error:\n"
        "- Ensure the file is not corrupted, not password-protected, and follows a recognizable MCQ format."
    )


def parse_question(text: str) -> Optional[Tuple[Optional[int], str, int]]:
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


def parse_option(text: str) -> Optional[Tuple[str, str, int]]:
    text_stripped = text.strip()
    m = OPTION_RE.match(text_stripped)
    if not m:
        return None
    prefix_len = m.start(2)
    return m.group(1).upper(), m.group(2).strip(), prefix_len


def parse_answer(text: str, current_options: Optional[List[str]] = None) -> Optional[str]:
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
                    content = opt[len(letter) + 2:].strip()
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


def parse_level(text: str) -> Optional[str]:
    m = LEVEL_RE.match(text.strip())
    if not m:
        return None
    return "Level: " + m.group(1).strip()


def paragraphs_to_questions(paragraphs, warnings_list=None):
    questions = []
    current = None

    def save(q):
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
            save(current)
            num, body, prefix_len = result
            q_elements = copy.deepcopy(elements)
            strip_xml_prefix(q_elements, prefix_len)

            current = Question(
                num=num,
                question=body,
                question_xml=q_elements,
            )

        elif current is not None:
            lower_text = text_stripped.lower()
            if lower_text.startswith('options:'):
                opts_part = text_stripped.split(':', 1)[1]
                prefix_len = text_stripped.index(opts_part)

                opts_line_elements = copy.deepcopy(elements)
                strip_xml_prefix(opts_line_elements, prefix_len)

                split_options_xml = split_xml_elements_by_separator(opts_line_elements, "|")
                opts = [o.strip() for o in opts_part.split('|')]
                for idx, opt_str in enumerate(opts):
                    opt_str = opt_str.strip()
                    if idx < len(split_options_xml):
                        opt_elements = split_options_xml[idx]
                    else:
                        opt_elements = [create_run_xml(opt_str)]

                    opt_result = parse_option(opt_str)
                    if opt_result:
                        letter, body, opt_prefix_len = opt_result
                        strip_xml_prefix(opt_elements, opt_prefix_len)
                        current.options.append(f"{letter}) {body}")
                        current.options_xml.append((letter, opt_elements))
                    else:
                        letter = chr(ord('A') + idx)
                        current.options.append(f"{letter}) {opt_str}")
                        current.options_xml.append((letter, opt_elements))
            elif current.options and (ans := parse_answer(text_stripped, current.options)):
                current.answer = ans
            elif (opt_result := parse_option(text_stripped)):
                letter, body, prefix_len = opt_result
                opt_elements = copy.deepcopy(elements)
                strip_xml_prefix(opt_elements, prefix_len)
                current.options.append(f"{letter}) {body}")
                current.options_xml.append((letter, opt_elements))
            elif (ans := parse_answer(text_stripped, current.options)):
                current.answer = ans
            elif (lvl := parse_level(text_stripped)):
                current.level = lvl
            else:
                if not current.options:
                    if current.question:
                        current.question += "\n" + text_stripped
                        current.question_xml.append(create_br_xml())
                    else:
                        current.question = text_stripped
                    current.question_xml.extend(copy.deepcopy(elements))

    save(current)
    return questions
