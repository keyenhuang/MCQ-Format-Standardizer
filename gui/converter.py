import threading
from pathlib import Path
from typing import List, Tuple, Callable

from parser import parse_docx, parse_txt, renumber_docx_inplace, renumber_txt_inplace, count_math_formulas, diagnose_error
from formatter import build_output_document, export_to_json, export_to_gift
from logger import get_logger

logger = get_logger()


class ConversionResult:
    def __init__(self, filename: str, status: str, math_count: int = 0,
                 warnings: list = None, error_msg: str = ""):
        self.filename = filename
        self.status = status
        self.math_count = math_count
        self.warnings = warnings or []
        self.error_msg = error_msg


def run_conversion(targets: List[Tuple[Path, Path]], mode: str,
                   on_progress: Callable[[int, int], None],
                   on_complete: Callable[[List[ConversionResult]], None],
                   export_format: str = "docx",
                   answers_at_bottom: bool = False):
    def _run():
        results = []
        total = len(targets)
        for i, (inp, out) in enumerate(targets):
            on_progress(i + 1, total)
            try:
                ext = inp.suffix.lower()
                if mode == "renumber":
                    if ext == '.docx':
                        renumber_docx_inplace(inp, out)
                    else:
                        renumber_txt_inplace(inp, out)
                    results.append(ConversionResult(inp.name, "success"))
                else:
                    warnings_list = []
                    parse_fn = parse_docx if ext == '.docx' else parse_txt
                    questions = parse_fn(inp, warnings_list)
                    if questions:
                        math_count = count_math_formulas(questions)
                        out_ext = export_format.lower()
                        if out_ext == "json":
                            content = export_to_json(questions)
                            with open(out, 'w', encoding='utf-8') as f:
                                f.write(content)
                        elif out_ext == "gift":
                            content = export_to_gift(questions)
                            with open(out, 'w', encoding='utf-8') as f:
                                f.write(content)
                        else:
                            build_output_document(questions, answers_at_bottom=answers_at_bottom).save(str(out))

                        results.append(ConversionResult(
                            inp.name, "success", math_count, warnings_list))
                    else:
                        results.append(ConversionResult(
                            inp.name, "error", error_msg="No questions found"))

            except (OSError, ValueError, ImportError) as e:
                logger.exception("Error processing %s", inp.name)
                diagnostic = diagnose_error(str(e))
                results.append(ConversionResult(inp.name, "error", error_msg=f"{e}\n\n{diagnostic}"))
        on_complete(results)

    threading.Thread(target=_run, daemon=True).start()
