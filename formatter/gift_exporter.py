import re
from typing import List
from parser.models import Question
from parser.engine import extract_answer_letters


def _escape_gift(text: str) -> str:
    if not text:
        return ""
    for ch in ("\\", "~", "=", "#", "{", "}", ":"):
        text = text.replace(ch, "\\" + ch)
    return text


def _format_weight(count: int) -> str:
    pct = 100.0 / count
    if pct.is_integer():
        return str(int(pct))
    return f"{pct:.5f}".rstrip("0").rstrip(".")


def export_to_gift(questions: List[Question]) -> str:
    gift_lines = []
    for idx, q in enumerate(questions, start=1):
        q_num = q.num if q.num is not None else idx
        title = f"::Q{q_num}:: "
        body = _escape_gift(q.question.strip())

        correct_letters = extract_answer_letters(q.answer)
        is_multi = len(correct_letters) > 1
        weight = _format_weight(len(correct_letters)) if is_multi else ""

        gift_body = [f"{title}{body} {{"]
        for opt in q.options:
            m = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE | re.DOTALL)
            if m:
                letter = m.group(1).upper()
                opt_text = _escape_gift(m.group(2).strip())
                if letter in correct_letters:
                    prefix = f"~%{weight}%" if is_multi else "="
                    gift_body.append(f"  {prefix}{opt_text}")
                else:
                    gift_body.append(f"  ~{opt_text}")
            else:
                gift_body.append(f"  ~{_escape_gift(opt)}")

        if q.explanation:
            exp_clean = _escape_gift(q.explanation.strip())
            gift_body.append(f"  #### {exp_clean}")

        gift_body.append("}")
        gift_lines.append("\n".join(gift_body))

    return "\n\n".join(gift_lines)

