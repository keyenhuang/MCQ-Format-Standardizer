import re
import copy
from dataclasses import replace
from docx import Document

from parser.engine import extract_answer_letters
from logger import get_logger

logger = get_logger()


def renumber_questions(questions, start: int = 1):
    return [replace(q, num=i) for i, q in enumerate(questions, start=start)]


def _add_run_with_text(paragraph, text, bold=False):
    run = paragraph.add_run(text)
    if bold:
        run.bold = True
    return run


def _extract_answer_letter(answer_text):
    letters = extract_answer_letters(answer_text)
    return ", ".join(letters) if letters else ""


def _append_xml_elements(paragraph, elements):
    for child in elements:
        paragraph._element.append(copy.deepcopy(child))


def _remove_default_paragraph(doc):
    if doc.paragraphs and doc.paragraphs[0].text == '':
        p = doc.paragraphs[0]
        p._element.getparent().remove(p._element)


def _add_option_paragraphs(doc, q, normal):
    if q.options_xml:
        for letter, opt_elements in q.options_xml:
            p_opt = doc.add_paragraph(style=normal)
            _add_run_with_text(p_opt, f"{letter}. ")
            _append_xml_elements(p_opt, opt_elements)
    else:
        for opt in q.options:
            opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE | re.DOTALL)
            if opt_match:
                doc.add_paragraph(f"{opt_match.group(1).upper()}. {opt_match.group(2)}", style=normal)
            else:
                doc.add_paragraph(opt, style=normal)


def _add_answer_paragraph(doc, q, normal, ans_letter):
    if ans_letter:
        doc.add_paragraph(f"Answer: {ans_letter}", style=normal)
    elif q.answer:
        doc.add_paragraph(q.answer, style=normal)


def _add_question_paragraph(doc, q, normal):
    p_q = doc.add_paragraph(style=normal)
    _add_run_with_text(p_q, f"{q.num}. ")
    if q.question_xml:
        _append_xml_elements(p_q, q.question_xml)
    else:
        _add_run_with_text(p_q, q.question)


def _add_level_paragraph(doc, q, normal):
    if q.level:
        doc.add_paragraph(q.level, style=normal)


def _add_explanation_paragraph(doc, q, normal):
    if q.explanation_xml:
        p_exp = doc.add_paragraph(style=normal)
        _add_run_with_text(p_exp, "Explanation: ", bold=True)
        _append_xml_elements(p_exp, q.explanation_xml)
    elif q.explanation:
        p_exp = doc.add_paragraph(style=normal)
        _add_run_with_text(p_exp, "Explanation: ", bold=True)
        r_text = _add_run_with_text(p_exp, q.explanation)
        r_text.italic = True


def build_output_document(questions, answers_at_bottom: bool = False):
    questions = renumber_questions(questions, start=1)
    doc = Document()
    _remove_default_paragraph(doc)

    try:
        normal = doc.styles['Normal']
    except KeyError:
        normal = None

    for i, q in enumerate(questions):
        _add_question_paragraph(doc, q, normal)
        _add_option_paragraphs(doc, q, normal)

        if not answers_at_bottom:
            ans_letter = _extract_answer_letter(q.answer)
            _add_answer_paragraph(doc, q, normal, ans_letter)
            _add_level_paragraph(doc, q, normal)
            _add_explanation_paragraph(doc, q, normal)

        if i < len(questions) - 1:
            doc.add_paragraph('', style=normal)

    if answers_at_bottom:
        doc.add_paragraph('', style=normal)
        p_head = doc.add_paragraph(style=normal)
        _add_run_with_text(p_head, "--- Answer Key & Explanations ---", bold=True)
        for q in questions:
            ans_letter = _extract_answer_letter(q.answer)
            p_ans = doc.add_paragraph(style=normal)
            _add_run_with_text(p_ans, f"Q{q.num}: ", bold=True)
            _add_run_with_text(p_ans, ans_letter or q.answer or "N/A")
            _add_level_paragraph(doc, q, normal)
            _add_explanation_paragraph(doc, q, normal)

    return doc


