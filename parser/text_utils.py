import locale
from pathlib import Path
from typing import List

from logger import get_logger

logger = get_logger()


def read_text_file(filepath: Path) -> List[str]:
    encodings = ['utf-8', 'gb18030', 'utf-16', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.readlines()
        except (UnicodeDecodeError, LookupError):
            continue

    sys_encoding = locale.getpreferredencoding()
    try:
        with open(filepath, 'r', encoding=sys_encoding, errors='replace') as f:
            return f.readlines()
    except OSError as e:
        logger.warning("Failed to read %s: %s", filepath, e)
        return []
