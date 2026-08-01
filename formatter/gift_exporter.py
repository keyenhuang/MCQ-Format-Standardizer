import re
from typing import List
from parser.models import Question


def _extract_letters(answer_text: str) -> List[str]:
    if not answer_text:
        return []
    cleaned = answer_text.replace("Answer:", "").replace("答案:", "").strip()
    return [l.upper() for l in re.findall(r'\b[A-H]\b', cleaned)]


def export_to_gift(questions: List[Question]) -> str:
    gift_lines = []
    for q in questions:
        title = f"::Q{q.num or 1}:: " if q.num else ""
        body = q.question.strip().replace("{", "\\{").replace("}", "\\}")

        correct_letters = _extract_letters(q.answer)

        gift_body = [f"{title}{body} {{"]
        for opt in q.options:
            m = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
            if m:
                letter = m.group(1).upper()
                opt_text = m.group(2).strip().replace("{", "\\{").replace("}", "\\}")
                if letter in correct_letters:
                    gift_body.append(f"  ={opt_text}")
                else:
                    gift_body.append(f"  ~{opt_text}")
            else:
                gift_body.append(f"  ~{opt}")

        if q.explanation:
            exp_clean = q.explanation.strip().replace("{", "\\{").replace("}", "\\}")
            gift_body.append(f"  #### {exp_clean}")

        gift_body.append("}")
        gift_lines.append("\n".join(gift_body))

    return "\n\n".join(gift_lines)
