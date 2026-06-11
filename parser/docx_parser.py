from pathlib import Path
from docx import Document
from parser.base import _paragraphs_to_questions, QUESTION_RE_INPLACE

def parse_docx(filepath: Path, warnings_list=None):
    doc = Document(str(filepath))
    return _paragraphs_to_questions(doc.paragraphs, warnings_list)

def renumber_docx_inplace(filepath: Path, output_path: Path):
    doc = Document(str(filepath))
    current_num = 1
    for para in doc.paragraphs:
        text = para.text
        m = QUESTION_RE_INPLACE.match(text)
        if m:
            prefix = m.group(1)
            old_num = m.group(2)
            sep = m.group(3)
            body = m.group(4)
            
            p_old = f"{prefix}{old_num}{sep}"
            p_new = f"{prefix}{current_num}{sep}"
            current_num += 1
            
            if para.runs:
                remaining_len = len(p_old)
                first_run_modified = False
                
                for run in para.runs:
                    run_len = len(run.text)
                    if run_len == 0:
                        continue
                    
                    if not first_run_modified:
                        if run_len >= remaining_len:
                            run.text = p_new + run.text[remaining_len:]
                            remaining_len = 0
                        else:
                            run.text = p_new
                            remaining_len -= run_len
                        first_run_modified = True
                    else:
                        if remaining_len > 0:
                            if run_len >= remaining_len:
                                run.text = run.text[remaining_len:]
                                remaining_len = 0
                            else:
                                run.text = ""
                                remaining_len -= run_len
                        else:
                            break
            else:
                para.text = f"{prefix}{current_num}{sep}{body}"
    doc.save(str(output_path))
