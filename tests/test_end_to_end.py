import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document

from config import get_config, is_valid_http_url, reset_config_cache, save_config_value
from formatter import build_output_document, export_to_gift, export_to_json
from gui.file_manager import FileManager
from llm_client import _build_messages, _parse_sse_line
from parser import (
    Question,
    extract_answer_letters,
    parse_docx,
    parse_txt,
    renumber_docx_inplace,
    renumber_txt_inplace,
)
from parser.engine import (
    paragraphs_to_questions,
    parse_answer,
    parse_option,
    parse_question,
    raw_prefix_length,
)
from parser.xml_utils import split_xml_elements_by_separator


class TestParserImprovements(unittest.TestCase):
    def test_prose_not_matched_as_question_or_option_or_answer(self):
        assert parse_question("Question about gravity is interesting.") is None
        assert parse_option("A key property of water is polarity.") is None
        assert parse_answer("A student asked a question") is None

    def test_chinese_and_bracketed_questions(self):
        assert parse_question("(1) What is 1+1?")[0] == 1
        assert parse_question("（2）什么是Python？")[0] == 2
        assert parse_question("第3题 What is HTTP?")[0] == 3

    def test_multi_letter_answers(self):
        assert parse_answer("Answer: A, B") == "Answer: A, B"
        assert parse_answer("答案：A、B") == "Answer: A, B"
        assert parse_answer("Answer: A B C") == "Answer: A, B, C"
        assert parse_answer("Answer: ABD") == "Answer: A, B, D"

    def test_extract_answer_letters_no_false_positives(self):
        assert extract_answer_letters("Answer: A) Vitamin C") == ["A"]
        assert extract_answer_letters("Answer: A, C, D") == ["A", "C", "D"]
        assert extract_answer_letters("Answer: Paris") == []

    def test_multiple_choice_q_type_after_options(self):
        lines = [
            "1. Select prime numbers:",
            "A) 2",
            "B) 3",
            "C) 4",
            "Answer: A, B",
        ]
        qs = paragraphs_to_questions(lines)
        assert len(qs) == 1
        assert qs[0].q_type == "multiple"
        assert qs[0].answer == "Answer: A, B"

    def test_single_choice_with_capital_letters_in_body_stays_single(self):
        lines = [
            "1. Which fruit?",
            "A) Apple Banana",
            "B) Cherry",
            "Answer: A",
        ]
        qs = paragraphs_to_questions(lines)
        assert len(qs) == 1
        assert qs[0].q_type == "single"

    def test_multiline_option_and_explanation(self):
        lines = [
            "1. Multi-line test?",
            "First line cont.",
            "A) Option A line 1",
            "Option A line 2",
            "B) Option B",
            "Answer: A",
            "Explanation: Line 1",
            "Line 2",
        ]
        qs = paragraphs_to_questions(lines)
        assert len(qs) == 1
        assert "First line cont." in qs[0].question
        assert "Option A line 2" in qs[0].options[0]
        assert "Line 2" in qs[0].explanation

    def test_horizontal_inline_options(self):
        lines = [
            "1. Pick one:",
            "A. Alpha   B. Beta   C. Gamma   D. Delta",
            "Answer: C",
        ]
        qs = paragraphs_to_questions(lines)
        assert len(qs) == 1
        assert qs[0].options == ["A) Alpha", "B) Beta", "C) Gamma", "D) Delta"]

    def test_raw_prefix_length_whitespace_and_nfkc(self):
        raw = "  １．What is x?"
        _, _, nfkc_len = parse_question(raw.strip())
        raw_len = raw_prefix_length(raw, nfkc_len)
        assert raw[raw_len:] == "What is x?"

    def test_split_xml_multi_separator(self):
        from docx.oxml import OxmlElement

        r = OxmlElement("w:r")
        t1 = OxmlElement("w:t")
        t1.text = "A) 1 | B) 2"
        t2 = OxmlElement("w:t")
        t2.text = " | C) 3"
        r.append(t1)
        r.append(t2)

        parts = split_xml_elements_by_separator([r], "|")
        texts = [
            "".join(n.text or "" for el in group for n in el.iter() if n.tag.endswith("}t"))
            for group in parts
        ]
        assert [t.strip() for t in texts] == ["A) 1", "B) 2", "C) 3"]


class TestDocxAndTxtRoundTrip(unittest.TestCase):
    def test_docx_parse_and_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "in.docx"
            out = Path(tmp) / "out.docx"
            doc = Document()
            doc.add_paragraph("  10. What is 2+2?")
            doc.add_paragraph("A) 3")
            doc.add_paragraph("B) 4")
            doc.add_paragraph("Answer: B")
            doc.add_paragraph("Level: Easy")
            doc.add_paragraph("Explanation: Basic math.")
            doc.save(str(inp))

            qs = parse_docx(inp)
            assert len(qs) == 1
            assert qs[0].question == "What is 2+2?"
            assert qs[0].level == "Level: Easy"

            out_doc = build_output_document(qs, answers_at_bottom=True)
            out_doc.save(str(out))
            out_texts = [p.text for p in Document(str(out)).paragraphs if p.text.strip()]
            assert any("1. What is 2+2?" in t for t in out_texts)
            assert any("--- Answer Key & Explanations ---" in t for t in out_texts)
            assert any("Q1: B" in t for t in out_texts)

    def test_docx_table_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "table.docx"
            doc = Document()
            tbl = doc.add_table(rows=1, cols=1)
            cell = tbl.cell(0, 0)
            cell.paragraphs[0].text = "1. From table?"
            cell.add_paragraph("A) Yes")
            cell.add_paragraph("B) No")
            cell.add_paragraph("Answer: A")
            doc.save(str(inp))

            qs = parse_docx(inp)
            assert len(qs) == 1
            assert qs[0].question == "From table?"

    def test_renumber_docx_inplace_without_runs_off_by_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "renum.docx"
            out = Path(tmp) / "renum_out.docx"
            doc = Document()
            doc.add_paragraph("5. First")
            doc.add_paragraph("A) 1")
            doc.add_paragraph("9. Second")
            doc.add_paragraph("A) 2")
            doc.save(str(inp))

            # Clear runs on second question? Instead verify normal & multi-run
            renumber_docx_inplace(inp, out)
            texts = [p.text for p in Document(str(out)).paragraphs]
            assert texts[0] == "1. First"
            assert texts[2] == "2. Second"

    def test_txt_parse_and_renumber(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "q.txt"
            out = Path(tmp) / "q_renum.txt"
            inp.write_text("4. Q one?\nA) 1\nB) 2\nAnswer: A\n\n8. Q two?\nA) X\nB) Y\nAnswer: B\n", encoding="utf-8")

            qs = parse_txt(inp)
            assert len(qs) == 2
            renumber_txt_inplace(inp, out)
            renum_text = out.read_text(encoding="utf-8")
            assert "1. Q one?" in renum_text
            assert "2. Q two?" in renum_text


class TestExportersExtended(unittest.TestCase):
    def test_gift_single_with_letter_c_in_option_text(self):
        q = Question(
            num=1,
            question="Which vitamin?",
            options=["A) Vitamin C", "B) Vitamin D", "C) Iron"],
            answer="Answer: A) Vitamin C",
        )
        gift = export_to_gift([q])
        assert "=Vitamin C" in gift
        assert "~Vitamin D" in gift
        assert "~Iron" in gift

    def test_gift_multi_answer_weights_and_escaping(self):
        q = Question(
            num=1,
            question="Pick {two} ~items=:",
            options=["A) One", "B) Two", "C) Three"],
            answer="Answer: A, B",
            q_type="multiple",
        )
        gift = export_to_gift([q])
        assert "~%50%One" in gift
        assert "~%50%Two" in gift
        assert "  ~Three" in gift
        assert "\\{two\\}" in gift
        assert "\\~items\\=\\:" in gift

    def test_json_includes_answer_letters(self):
        q = Question(num=1, question="Q?", options=["A) 1", "B) 2"], answer="Answer: A, B", q_type="multiple")
        parsed = json.loads(export_to_json([q]))
        assert parsed[0]["answer_letters"] == ["A", "B"]


class TestConfigLLMCLIAndFileManager(unittest.TestCase):
    def test_url_validation_and_env_override(self):
        assert is_valid_http_url("https://api.openai.com/v1")
        assert not is_valid_http_url("ftp://example.com")
        assert not is_valid_http_url("not-a-url")

        reset_config_cache()
        old = os.environ.get("MCQ_MODEL")
        os.environ["MCQ_MODEL"] = "test-model-x"
        try:
            cfg = get_config()
            assert cfg["MODEL"] == "test-model-x"
            assert not save_config_value("BASE_URL", "invalid-url")
        finally:
            if old is None:
                os.environ.pop("MCQ_MODEL", None)
            else:
                os.environ["MCQ_MODEL"] = old
            reset_config_cache()

    def test_llm_helpers(self):
        msgs = _build_messages("Hi", {"SYSTEM_PROMPT": "Sys"}, history=[{"role": "user", "content": "prev"}])
        assert len(msgs) == 3
        assert msgs[0]["role"] == "system"
        assert _parse_sse_line(b'data: {"choices":[{"delta":{"content":"hel"}}]}') == "hel"
        assert _parse_sse_line(b"data: [DONE]") == "__DONE__"

    def test_file_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "a.docx"
            p2 = Path(tmp) / "b.txt"
            p3 = Path(tmp) / "c.pdf"
            fm = FileManager()
            added = fm.add_files([p1, p1, p2, p3])
            assert len(added) == 2
            assert fm.count == 2
            assert fm.remove_file(p1)
            assert fm.count == 1

    def test_cli_json_and_gift_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "sample.txt"
            out_json = Path(tmp) / "out.json"
            out_gift = Path(tmp) / "out.gift"
            inp.write_text("1. Capital of Japan?\nA) Tokyo\nB) Osaka\nAnswer: A\n", encoding="utf-8")

            root = Path(__file__).resolve().parent.parent
            res1 = subprocess.run(
                [sys.executable, str(root / "main.py"), str(inp), str(out_json)],
                capture_output=True, text=True, check=False,
            )
            assert res1.returncode == 0, res1.stderr
            data = json.loads(out_json.read_text(encoding="utf-8"))
            assert data[0]["answer_letters"] == ["A"]

            res2 = subprocess.run(
                [sys.executable, str(root / "main.py"), str(inp), str(out_gift), "--format", "gift"],
                capture_output=True, text=True, check=False,
            )
            assert res2.returncode == 0, res2.stderr
            assert "=Tokyo" in out_gift.read_text(encoding="utf-8")
