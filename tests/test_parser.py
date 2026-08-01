import unittest
from parser.engine import parse_question, parse_option, parse_answer, parse_level, diagnose_error


class TestParseQuestion(unittest.TestCase):

    def test_numbered_question(self):
        result = parse_question("1. What is the capital of France?")
        assert result is not None
        num, body, prefix_len = result
        assert num == 1
        assert "capital of France" in body

    def test_q_prefix_question(self):
        result = parse_question("Q1: What is 2+2?")
        assert result is not None
        num, body, _ = result
        assert num == 1
        assert "2+2" in body

    def test_question_without_number(self):
        result = parse_question("Q: What is Python?")
        assert result is not None
        num, body, _ = result
        assert num is None
        assert "Python" in body

    def test_fullwidth_numbered_question(self):
        result = parse_question("１．What is the capital of France?")
        assert result is not None
        num, body, _ = result
        assert num == 1
        assert "capital of France" in body

    def test_unparseable_text(self):
        result = parse_question("This is just a sentence.")
        assert result is None

    def test_empty_string(self):
        assert parse_question("") is None


class TestParseOption(unittest.TestCase):
    def test_letter_option(self):
        result = parse_option("A) Paris")
        assert result is not None
        letter, body, _ = result
        assert letter == "A"
        assert body == "Paris"

    def test_dot_option(self):
        result = parse_option("B. London")
        assert result is not None
        letter, body, _ = result
        assert letter == "B"
        assert body == "London"

    def test_lowercase_option(self):
        result = parse_option("c) Berlin")
        assert result is not None
        letter, body, _ = result
        assert letter == "C"
        assert body == "Berlin"

    def test_bracket_option(self):
        result = parse_option("(D) Madrid")
        assert result is not None
        letter, body, _ = result
        assert letter == "D"
        assert body == "Madrid"

    def test_fullwidth_option(self):
        result = parse_option("Ａ．Paris")
        assert result is not None
        letter, body, _ = result
        assert letter == "A"
        assert body == "Paris"

    def test_fullwidth_bracket_option(self):
        result = parse_option("（Ｂ）London")
        assert result is not None
        letter, body, _ = result
        assert letter == "B"
        assert body == "London"

    def test_unparseable_option(self):
        result = parse_option("Not an option")
        assert result is None


class TestParseAnswer(unittest.TestCase):
    def test_answer_with_letter(self):
        result = parse_answer("Answer: A) Paris")
        assert result is not None
        assert "A)" in result
        assert "Paris" in result

    def test_answer_with_keyword(self):
        result = parse_answer("Answer: A")
        assert result is not None
        assert "A)" in result

    def test_answer_chinese(self):
        result = parse_answer("答案: A")
        assert result is not None
        assert "A)" in result

    def test_answer_without_letter(self):
        result = parse_answer("Answer: Paris", ["A) Paris", "B) London"])
        assert result is not None
        assert "A)" in result

    def test_unparseable_answer(self):
        assert parse_answer("This is not an answer") is None


class TestParseLevel(unittest.TestCase):
    def test_level(self):
        result = parse_level("Level: Easy")
        assert result is not None
        assert "Easy" in result

    def test_level_chinese_colon(self):
        result = parse_level("Level：Hard")
        assert result is not None
        assert "Hard" in result

    def test_not_a_level(self):
        assert parse_level("Just some text") is None


class TestDiagnoseError(unittest.TestCase):
    def test_permission_error(self):
        msg = diagnose_error("Permission denied")
        assert "File Locked" in msg

    def test_not_found_error(self):
        msg = diagnose_error("No such file")
        assert "File Not Found" in msg

    def test_bad_zip_error(self):
        msg = diagnose_error("Bad zip file")
        assert "Invalid Word Document" in msg

    def test_unknown_error(self):
        msg = diagnose_error("Something unexpected happened")
        assert "Unknown Conversion" in msg
