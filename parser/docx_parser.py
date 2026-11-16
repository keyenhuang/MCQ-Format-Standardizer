from pathlib import Path
from docx import Document
from parser.engine import paragraphs_to_questions
from parser.regex import QUESTION_RE_INPLACE


def _iter_table_paragraphs(doc):
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    yield para


def parse_docx(filepath: Path, warnings_list=None):
    doc = Document(str(filepath))
    questions = paragraphs_to_questions(doc.paragraphs, warnings_list)
    if not questions and doc.tables:
        questions = paragraphs_to_questions(list(_iter_table_paragraphs(doc)), warnings_list)
    return questions


def _replace_para_prefix(para, p_old: str, p_new: str, fallback_text: str) -> None:
    if not para.runs:
        para.text = fallback_text
        return

    remaining_len = len(p_old)
    first_run_modified = False
    for run in para.runs:
        run_len = len(run.text)
        if run_len == 0:
            continue

        if not first_run_modified:
            if run_len >= remaining_len:
                run.text = p_new + run.text[remaining_len:]
                return
            run.text = p_new
            remaining_len -= run_len
            first_run_modified = True
        elif remaining_len > 0:
            if run_len >= remaining_len:
                run.text = run.text[remaining_len:]
                return
            run.text = ""
            remaining_len -= run_len


def _renumber_paragraphs(paragraphs, start_num: int = 1) -> int:
    current_num = start_num
    for para in paragraphs:
        m = QUESTION_RE_INPLACE.match(para.text)
        if not m:
            continue
        prefix, old_num_str, sep, body = m.group(1), m.group(2), m.group(3), m.group(4)
        new_num = current_num
        current_num += 1
        p_old = f"{prefix}{old_num_str}{sep}"
        p_new = f"{prefix}{new_num}{sep}"
        _replace_para_prefix(para, p_old, p_new, f"{p_new}{body}")
    return current_num


def renumber_docx_inplace(filepath: Path, output_path: Path):
    doc = Document(str(filepath))
    next_num = _renumber_paragraphs(doc.paragraphs, start_num=1)
    if next_num == 1 and doc.tables:
        _renumber_paragraphs(_iter_table_paragraphs(doc), start_num=1)
    doc.save(str(output_path))

