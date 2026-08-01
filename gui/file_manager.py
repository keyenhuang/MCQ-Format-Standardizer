from pathlib import Path
from typing import List


class FileManager:
    def __init__(self):
        self.input_files: List[Path] = []

    def add_files(self, paths: List[Path]) -> List[Path]:
        new_files = [p for p in paths if p not in self.input_files]
        self.input_files.extend(new_files)
        return new_files

    def clear(self):
        self.input_files.clear()

    @property
    def count(self) -> int:
        return len(self.input_files)

    @property
    def summary(self) -> str:
        if not self.input_files:
            return "No files selected"
        names = ", ".join(f.name for f in self.input_files)
        if len(names) > 60:
            names = names[:57] + "..."
        return f"Selected {len(self.input_files)} files: {names}" if len(self.input_files) > 1 \
            else f"Selected: {self.input_files[0].name}"
