#!/usr/bin/env python3
"""
MCQ Converter - Main Entry Point
================================
Supports launching the Tkinter GUI app or running tasks via CLI arguments.
"""

import sys
from pathlib import Path

# Add script directory to system path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from parser import (
    parse_docx, parse_txt,
    renumber_docx_inplace, renumber_txt_inplace
)
from formatter import build_output_document
from gui.app import MCQConverterApp

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ['--gui', '-g']:
        app = MCQConverterApp()
        app.mainloop()
    else:
        only_renumber = False
        if '--only-renumber' in args:
            only_renumber = True
            args.remove('--only-renumber')
        if '-r' in args:
            only_renumber = True
            args.remove('-r')
            
        if len(args) < 1:
            print("Usage: python main.py <input_file> [<output_file>] [--only-renumber]", file=sys.stderr)
            sys.exit(1)
            
        inp = Path(args[0])
        out = Path(args[1]) if len(args) > 1 else inp.with_name(inp.stem + "_MCQ.docx")
        
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
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
