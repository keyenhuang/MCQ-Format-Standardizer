import threading
from pathlib import Path
from typing import List, Tuple, Callable

from parser import (
    parse_docx, parse_txt,
    renumber_docx_inplace, renumber_txt_inplace,
    count_math_formulas, diagnose_error
)
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


def _write_standardized(questions, out: Path, export_format: str, answers_at_bottom: bool) -> None:
    out_ext = export_format.lower()
    if out_ext == "json":
        out.write_text(export_to_json(questions), encoding="utf-8")
    elif out_ext == "gift":
        out.write_text(export_to_gift(questions), encoding="utf-8")
    else:
        build_output_document(questions, answers_at_bottom=answers_at_bottom).save(str(out))


def _process_target(inp: Path, out: Path, mode: str, export_format: str, answers_at_bottom: bool) -> ConversionResult:
    ext = inp.suffix.lower()
    out.parent.mkdir(parents=True, exist_ok=True)

    if mode == "renumber":
        if ext == ".docx":
            renumber_docx_inplace(inp, out)
        else:
            renumber_txt_inplace(inp, out)
        return ConversionResult(inp.name, "success")

    warnings_list = []
    parse_fn = parse_docx if ext == ".docx" else parse_txt
    questions = parse_fn(inp, warnings_list)
    if not questions:
        return ConversionResult(inp.name, "error", error_msg="No questions found")

    math_count = count_math_formulas(questions)
    _write_standardized(questions, out, export_format, answers_at_bottom)
    return ConversionResult(inp.name, "success", math_count, warnings_list)


def run_conversion(targets: List[Tuple[Path, Path]], mode: str,
                   on_progress: Callable[[int, int], None],
                   on_complete: Callable[[List[ConversionResult]], None],
                   export_format: str = "docx",
                   answers_at_bottom: bool = False):
    def _run():
        results = []
        total = len(targets)
        on_progress(0, total)
        for i, (inp, out) in enumerate(targets):
            try:
                res = _process_target(inp, out, mode, export_format, answers_at_bottom)
                results.append(res)
            except Exception as e:
                logger.exception("Error processing %s", inp.name)
                diagnostic = diagnose_error(str(e))
                results.append(ConversionResult(inp.name, "error", error_msg=f"{e}\n\n{diagnostic}"))
            finally:
                on_progress(i + 1, total)
        on_complete(results)

    threading.Thread(target=_run, daemon=True).start()

