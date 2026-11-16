from pathlib import Path
from typing import List


class FileManager:
    def __init__(self):
        self.input_files: List[Path] = []

    def add_files(self, paths: List[Path]) -> List[Path]:
        existing = {p.resolve() for p in self.input_files}
        new_files = []
        for path in paths:
            p = Path(path)
            if p.suffix.lower() not in (".docx", ".txt"):
                continue
            resolved = p.resolve()
            if resolved not in existing:
                existing.add(resolved)
                self.input_files.append(p)
                new_files.append(p)
        return new_files

    def remove_file(self, path: Path) -> bool:
        resolved = Path(path).resolve()
        for idx, existing in enumerate(self.input_files):
            if existing.resolve() == resolved:
                self.input_files.pop(idx)
                return True
        return False

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

