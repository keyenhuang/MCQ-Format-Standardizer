import re

QUESTION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:'
    r'(?:\u7b2c\s*)?(?:Q:?\s*|Question\s+)(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\s\u9898]*\s*(.*)'
    r'|'
    r'(?:\u7b2c\s*)?(\d+)[.:\uFF0E\u3001)\uFF09\]\u3011\u9898]+\s*(.*)'
    r'|'
    r'(?:\(|\[|\u3010|\uFF08)(\d+)(?:\)|\]|\u3011|\uFF09)[.:\uFF0E\u3001\s\u9898]*\s*(.*)'
    r'|'
    r'(?:Q|Question)[:\uFF1A]\s*(.*)'
    r')',
    re.IGNORECASE | re.DOTALL
)

OPTION_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:'
    r'(?:\(|\[|\u3010|\uFF08)([A-Ha-h])(?:\)|\]|\u3011|\uFF09)[.:\uFF0E\u3001\s]*\s*(.*)'
    r'|'
    r'([A-Ha-h])(?:[\)\.\uFF0E\u3001\]\u3011\uFF09:\uFF1A\t]|\s{2,})\s*(.*)'
    r')',
    re.DOTALL
)

INLINE_OPTION_SPLIT_RE = re.compile(
    r'(?:\s{2,}|\t+)(?=(?:\(|\[|\u3010|\uFF08)?[A-Ha-h](?:[\)\.\uFF0E\u3001\]\u3011\uFF09:\uFF1A\t]|\s{2,}))'
)

ANSWER_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:'
    r'(?:Answer|Ans|Key|\u6b63\u786e\u7b54\u6848|\u3010\u7b54\u6848\u3011|\u7b54\u6848)[:\uFF1A\s]\s*(.*)'
    r'|'
    r'A[:\uFF1A]\s*(.*)'
    r')',
    re.IGNORECASE | re.DOTALL
)

LEVEL_RE = re.compile(
    r'^(?:[\ufeff\s]*)(?:Level|Difficulty|\u96be\u5ea6|\u3010\u96be\u5ea6\u3011)[:\uFF1A\s]+\s*(.*)',
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
