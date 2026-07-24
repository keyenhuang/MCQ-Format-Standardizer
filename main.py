import sys
import traceback
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).parent.absolute()
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from logger import setup_logger, get_logger
from parser import (
    parse_docx, parse_txt,
    renumber_docx_inplace, renumber_txt_inplace
)
from formatter import build_output_document
from gui.app import MCQFormatStandardizerApp

logger = setup_logger()


def print_usage(prog):
    print(f"Usage: {prog} <input_file> [<output_file>] [--only-renumber|-r]", file=sys.stderr)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('--gui', '-g'):
        app = MCQFormatStandardizerApp()
        app.mainloop()
        return

    only_renumber = False
    filtered_args = []
    for a in args:
        if a in ('--only-renumber', '-r'):
            only_renumber = True
        else:
            filtered_args.append(a)
    args = filtered_args

    if len(args) < 1:
        print_usage(sys.argv[0])
        sys.exit(1)

    inp = Path(args[0])
    out = Path(args[1]) if len(args) > 1 else inp.with_name(inp.stem + "_standardized.docx")

    try:
        if only_renumber:
            if inp.suffix.lower() == '.docx':
                renumber_docx_inplace(inp, out)
            else:
                renumber_txt_inplace(inp, out)
            print(f"Success: Renumbered '{inp.name}' -> '{out.name}'")
        else:
            questions = parse_docx(inp) if inp.suffix.lower() == '.docx' else parse_txt(inp)
            if questions:
                build_output_document(questions).save(str(out))
                print(f"Success: Converted '{inp.name}' -> '{out.name}'")
            else:
                print("No questions found or failed to parse input.", file=sys.stderr)
                sys.exit(1)
    except Exception as e:
        logger.error("Conversion failed: %s", e)
        logger.debug(traceback.format_exc())
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
