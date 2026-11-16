import argparse
import logging
import sys
import traceback
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).parent.absolute()
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from logger import setup_logger
from parser import (
    parse_docx, parse_txt,
    renumber_docx_inplace, renumber_txt_inplace
)
from formatter import build_output_document, export_to_json, export_to_gift

logger = setup_logger()


def build_arg_parser() -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        prog="mcq-standardizer",
        description="Batch parse, standardize, and renumber MCQ documents (.docx / .txt).",
    )
    arg_parser.add_argument("input_file", nargs="?", help="Input .docx or .txt file path")
    arg_parser.add_argument("output_file", nargs="?", help="Optional output file path")
    arg_parser.add_argument(
        "-g", "--gui", action="store_true",
        help="Launch the desktop GUI application"
    )
    arg_parser.add_argument(
        "-r", "--only-renumber", action="store_true",
        help="Renumber questions in-place while preserving existing styling"
    )
    arg_parser.add_argument(
        "-f", "--format", choices=["docx", "json", "gift"], default=None,
        help="Output format (defaults to output extension or docx)"
    )
    arg_parser.add_argument(
        "-b", "--answers-at-bottom", action="store_true",
        help="Place answer key and explanations in a separate section at the end (.docx only)"
    )
    arg_parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging"
    )
    return arg_parser


def _resolve_output_and_format(inp: Path, output_arg: str | None, fmt_arg: str | None, only_renumber: bool):
    if only_renumber:
        out = Path(output_arg) if output_arg else inp.with_name(f"{inp.stem}_renumbered{inp.suffix}")
        return out, inp.suffix.lower().lstrip(".")

    if fmt_arg:
        fmt = fmt_arg.lower()
    elif output_arg and Path(output_arg).suffix.lower() in (".json", ".gift", ".docx"):
        fmt = Path(output_arg).suffix.lower().lstrip(".")
    else:
        fmt = "docx"

    out = Path(output_arg) if output_arg else inp.with_name(f"{inp.stem}_standardized.{fmt}")
    return out, fmt


def _run_cli(args: argparse.Namespace) -> None:
    inp = Path(args.input_file)
    if not inp.exists():
        print(f"Error: Input file not found: {inp}", file=sys.stderr)
        sys.exit(1)

    out, fmt = _resolve_output_and_format(inp, args.output_file, args.format, args.only_renumber)
    out.parent.mkdir(parents=True, exist_ok=True)
    inp_ext = inp.suffix.lower()

    if args.only_renumber:
        if inp_ext == ".docx":
            renumber_docx_inplace(inp, out)
        else:
            renumber_txt_inplace(inp, out)
        print(f"Success: Renumbered '{inp.name}' -> '{out.name}'")
        return

    questions = parse_docx(inp) if inp_ext == ".docx" else parse_txt(inp)
    if not questions:
        print("No questions found or failed to parse input.", file=sys.stderr)
        sys.exit(1)

    if fmt == "json":
        out.write_text(export_to_json(questions), encoding="utf-8")
    elif fmt == "gift":
        out.write_text(export_to_gift(questions), encoding="utf-8")
    else:
        build_output_document(questions, answers_at_bottom=args.answers_at_bottom).save(str(out))

    print(f"Success: Converted '{inp.name}' -> '{out.name}' ({len(questions)} questions)")


def main():
    arg_parser = build_arg_parser()
    args = arg_parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    if args.gui or not args.input_file:
        from gui.app import MCQFormatStandardizerApp
        app = MCQFormatStandardizerApp()
        app.mainloop()
        return

    try:
        _run_cli(args)
    except Exception as e:
        logger.error("Conversion failed: %s", e)
        logger.debug(traceback.format_exc())
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

