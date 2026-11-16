import json
from typing import List
from parser.models import Question
from parser.engine import extract_answer_letters


def export_to_json(questions: List[Question], indent: int = 2) -> str:
    data = []
    for q in questions:
        item = {
            "num": q.num,
            "q_type": q.q_type,
            "question": q.question,
            "options": q.options,
            "answer": q.answer,
            "answer_letters": extract_answer_letters(q.answer),
            "level": q.level if q.level else None,
            "explanation": q.explanation if q.explanation else None
        }
        data.append(item)
    return json.dumps(data, ensure_ascii=False, indent=indent)

