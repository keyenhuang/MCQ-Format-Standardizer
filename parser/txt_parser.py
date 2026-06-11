from pathlib import Path
from parser.text_utils import read_text_file
from parser.engine import paragraphs_to_questions
from parser.regex import QUESTION_RE_INPLACE


def parse_txt(filepath: Path, warnings_list=None):
    lines = [ln.rstrip('\n\r').strip() for ln in read_text_file(filepath)]
    return paragraphs_to_questions(lines, warnings_list)


def renumber_txt_inplace(filepath: Path, output_path: Path):
    lines = read_text_file(filepath)
    new_lines = []
    current_num = 1
    for line in lines:
        m = QUESTION_RE_INPLACE.match(line)
        if m:
            prefix = m.group(1)
            sep = m.group(3)
            body = m.group(4)
            new_lines.append(f"{prefix}{current_num}{sep}{body}")
            current_num += 1
        else:
            new_lines.append(line)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
