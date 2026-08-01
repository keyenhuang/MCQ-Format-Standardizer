import re
import copy
from dataclasses import replace
from docx import Document
from docx.oxml import OxmlElement

from parser.models import Question
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
    if not answer_text:
        return ""
    m = re.match(r'^Answer:\s*([A-H])(?:\)|\]|\.|\s|$)', answer_text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m2 = re.search(r'\b([A-H])\b', answer_text.replace('Answer:', ''), re.IGNORECASE)
    return m2.group(1).upper() if m2 else ""


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
            opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
            if opt_match:
                doc.add_paragraph(f"{opt_match.group(1).upper()}. {opt_match.group(2)}", style=normal)
            else:
                doc.add_paragraph(opt, style=normal)


def _add_answer_paragraph(doc, q, normal, ans_letter):
    if ans_letter:
        doc.add_paragraph(f"Answer: {ans_letter}", style=normal)
    else:
        doc.add_paragraph(q.answer, style=normal)


def _add_question_paragraph(doc, q, normal):
    p_q = doc.add_paragraph(style=normal)
    _add_run_with_text(p_q, f"{q.num}. ")
    if q.question_xml:
        _append_xml_elements(p_q, q.question_xml)
    else:
        _add_run_with_text(p_q, q.question)


def build_output_document(questions):
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

        ans_letter = _extract_answer_letter(q.answer)
        _add_answer_paragraph(doc, q, normal, ans_letter)

        if i < len(questions) - 1:
            doc.add_paragraph('', style=normal)

    return doc
