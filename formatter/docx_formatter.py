import re
import copy
from docx import Document

def _build_options_line(options):
    """'Options: A) ... | B) ... | C) ... | D) ...'"""
    return "Options: " + " | ".join(options)

def renumber_questions(questions, start: int = 1):
    """Return a new list of questions with sequentially reassigned `num`."""
    new = []
    for i, q in enumerate(questions, start=start):
        nq = q.copy()
        nq['num'] = i
        new.append(nq)
    return new

def build_output_document(questions):
    """Create a python-docx Document using the standard MCQ template structure."""
    questions = renumber_questions(questions, start=1)
    doc = Document()

    if doc.paragraphs and doc.paragraphs[0].text == '':
        p = doc.paragraphs[0]
        p._element.getparent().remove(p._element)

    try:
        normal = doc.styles['Normal']
    except KeyError:
        normal = None

    for i, q in enumerate(questions):
        p_q = doc.add_paragraph(style=normal)
        p_q.add_run(f"{q['num']}. ")
        
        if 'question_xml' in q and q['question_xml']:
            for child in q['question_xml']:
                p_q._element.append(copy.deepcopy(child))
        else:
            p_q.add_run(q['question'])

        if 'options_xml' in q and q['options_xml']:
            for letter, opt_elements in q['options_xml']:
                p_opt = doc.add_paragraph(style=normal)
                p_opt.add_run(f"{letter}. ")
                for child in opt_elements:
                    p_opt._element.append(copy.deepcopy(child))
        else:
            for opt in q['options']:
                opt_match = re.match(r'^([A-H])\)\s*(.*)', opt, re.IGNORECASE)
                if opt_match:
                    letter = opt_match.group(1).upper()
                    body = opt_match.group(2)
                    doc.add_paragraph(f"{letter}. {body}", style=normal)
                else:
                    doc.add_paragraph(opt, style=normal)

        ans_letter = ""
        if q['answer']:
            m = re.match(r'^Answer:\s*([A-H])(?:\)|\]|\.|\s|$)', q['answer'], re.IGNORECASE)
            if m:
                ans_letter = m.group(1).upper()
            else:
                m2 = re.search(r'\b([A-H])\b', q['answer'].replace('Answer:', ''), re.IGNORECASE)
                if m2:
                    ans_letter = m2.group(1).upper()
        
        if ans_letter:
            doc.add_paragraph(f"Answer: {ans_letter}", style=normal)
        else:
            doc.add_paragraph(q['answer'], style=normal)

        if i < len(questions) - 1:
            doc.add_paragraph('', style=normal)

    return doc
