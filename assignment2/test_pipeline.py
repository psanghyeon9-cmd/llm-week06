from collections import Counter
import contextlib
import io
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from classify import classify_review, parse_response
from mock_llm import mock_llm_call
from run_pipeline import load_reviews, print_summary, run_reviews


class ControlledRandom:
    def __init__(self, probability, kind="code_fence"):
        self.probability = probability
        self.kind = kind

    def random(self):
        return self.probability

    def choice(self, values):
        if self.kind not in values:
            raise AssertionError("Unknown injection kind")
        return self.kind


class PipelineTests(unittest.TestCase):
    def test_probability_boundary(self):
        below = mock_llm_call("", "배송", rng=ControlledRandom(0.1999))
        boundary = mock_llm_call("", "배송", rng=ControlledRandom(0.2))
        self.assertEqual(below["mock_response_kind"], "code_fence")
        self.assertEqual(boundary["mock_response_kind"], "normal")

    def test_normal_classroom_outputs_unchanged(self):
        for review, expected in (("배송", ("배송", "긍정", 4)), ("환불", ("환불", "부정", 2)), ("품질", ("품질", "긍정", 5)), ("문의", ("기타", "중립", 3))):
            with self.subTest(review=review):
                result = classify_review(review, rng=ControlledRandom(1.0))
                self.assertEqual((result["category"], result["sentiment"], result["score"]), expected)

    def test_fence_recovers_but_other_malformed_responses_fail(self):
        for kind in ("code_fence", "preamble", "truncated"):
            with self.subTest(kind=kind):
                stats = Counter()
                result = classify_review("배송 문의", rng=ControlledRandom(0.0, kind), diagnostics=stats)
                self.assertEqual(stats[kind], 1)
                if kind == "code_fence":
                    self.assertEqual(result["category"], "배송")
                    self.assertEqual(stats["code_fence_recovered"], 1)
                else:
                    self.assertIsNone(result)
                    self.assertEqual(stats["invalid_response"], 1)

    def test_schema_validation(self):
        valid = {"category": "배송", "sentiment": "긍정", "score": 4}
        invalid = [None, [], True, {}, {**valid, "score": True}, {**valid, "score": "4"}, {**valid, "score": 4.0}, {**valid, "score": 0}, {**valid, "score": 6}, {**valid, "category": "주문"}, {**valid, "sentiment": "모름"}, {**valid, "extra": 1}]
        for obj in invalid:
            with self.subTest(obj=obj):
                self.assertIsNone(parse_response(json.dumps(obj)))
        self.assertIsNone(parse_response(None))
        self.assertEqual(parse_response(json.dumps(valid)), valid)

    def test_parser_does_not_trust_mock_metadata(self):
        response = {"text": "not JSON", "mock_response_kind": "normal"}
        with patch("classify.mock_llm_call", return_value=response):
            self.assertIsNone(classify_review("배송"))

    def test_processing_continues_after_failed_rows(self):
        calls = [mock_llm_call("", "배송", rng=ControlledRandom(0.0, kind)) for kind in ("preamble", "code_fence", "truncated")]
        calls.append(mock_llm_call("", "품질", rng=ControlledRandom(1.0)))
        with patch("classify.mock_llm_call", side_effect=calls):
            summary, rows = run_reviews(["배송"] * 4)
        self.assertEqual((summary["processed"], summary["success"], summary["failed"]), (4, 2, 2))
        self.assertEqual(rows[-1]["category"], "품질")
        self.assertEqual(summary["malformed"] - summary["recovered_code_fence"], summary["failed"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            print_summary(summary, 42)
        self.assertEqual(output.getvalue().splitlines()[-1], "처리 4건 / 실패 2건")

    def test_invalid_inputs_count_as_failures_without_call(self):
        with patch("classify.mock_llm_call") as call:
            summary, _ = run_reviews(["", "   ", None])
            call.assert_not_called()
        self.assertEqual(summary["failed"], 3)
        self.assertEqual(summary["invalid_input"], 3)

    def test_csv_bom_and_missing_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reviews.csv"
            path.write_text('review_text,rating\n"배송, 좋아요",4\n', encoding="utf-8-sig")
            self.assertEqual(load_reviews(path), ["배송, 좋아요"])
            path.write_text("wrong\nvalue\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_reviews(path)

    def test_full_dataset_is_reproducible_and_balanced(self):
        reviews = load_reviews(Path(__file__).parent / "data/reviews_sample.csv")
        self.assertEqual(len(reviews), 200)
        first = run_reviews(reviews, rng=random.Random(42))
        second = run_reviews(reviews, rng=random.Random(42))
        self.assertEqual(first, second)
        summary, rows = first
        self.assertEqual(len(rows), 200)
        self.assertEqual(summary["normal"] + summary["malformed"], 200)
        self.assertEqual(summary["success"] + summary["failed"], 200)
        self.assertEqual(sum(summary["categories"].values()), summary["success"])
        self.assertEqual(summary["failed"], summary["malformed_by_kind"]["preamble"] + summary["malformed_by_kind"]["truncated"])
        self.assertEqual(summary["recovered_code_fence"], summary["malformed_by_kind"]["code_fence"])
        self.assertTrue(all(count > 0 for count in summary["malformed_by_kind"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
