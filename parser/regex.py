import re

QUESTION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:'
    r'(?:Q:?\s*|Question\s+)(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]*\s*(.*)'
    r'|'
    r'(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\u9898]+\s*(.*)'
    r'|'
    r'(?:Q|Question)[:\uFF1A\s]\s*(.*)'
    r')',
    re.IGNORECASE | re.DOTALL
)

OPTION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:\(|\[|\u3010|\uFF08)?([A-Ha-h])'
    r'(?:[\)\.\uFF0E\u3001\]\u3011\s\uFF09:\uFF1A])+\s*(.*)',
    re.DOTALL
)

ANSWER_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:Answer|Ans|Key|A|'
    r'\u6b63\u786e\u7b54\u6848|\u3010\u7b54\u6848\u3011|\u7b54\u6848)'
    r'[:\uFF1A\s]\s*(.*)',
    re.IGNORECASE | re.DOTALL
)

LEVEL_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:Level)[:\uFF1A\s]+\s*(.*)',
    re.IGNORECASE | re.DOTALL
)

EXPLANATION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:Explanation|Explain|Analysis|Solution|'
    r'\u89e3\u6790|\u3010\u89e3\u6790\u3011|\u9898\u89e3|\u89e3\u7b54)'
    r'[:\uFF1A\s]\s*(.*)',
    re.IGNORECASE | re.DOTALL
)

QUESTION_RE_INPLACE = re.compile(
    r'^([\ufeff\s]*(?:\u7b2c)?(?:Q:?|Question\s*)?)(\d+)'
    r'([.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]+\s*)(.*)',
    re.IGNORECASE | re.DOTALL
)

