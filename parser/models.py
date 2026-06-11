from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Question:
    num: Optional[int]
    question: str
    question_xml: list = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    options_xml: List[Tuple[str, list]] = field(default_factory=list)
    answer: str = ""
    level: str = ""
