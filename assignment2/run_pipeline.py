"""표준 라이브러리만 사용하며 실제 API·네트워크 호출은 없습니다."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import random

from classify import classify_review
from mock_llm import BAD_KINDS, BAD_RESPONSE_RATE


def load_reviews(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "review_text" not in reader.fieldnames:
            raise ValueError("CSV에 review_text 열이 필요합니다.")
        return [row["review_text"] for row in reader]


def run_reviews(reviews, *, rng=None):
    diagnostics = Counter()
    categories = Counter()
    outcomes = []
    failed = 0
    for number, review in enumerate(reviews, start=1):
        result = classify_review(review, rng=rng, diagnostics=diagnostics)
        if result is None:
            failed += 1
            outcomes.append({"row": number, "status": "failed", "category": "", "sentiment": "", "score": ""})
            continue
        categories[result["category"]] += 1
        outcomes.append({"row": number, "status": "ok", **result})

    processed = len(outcomes)
    success = processed - failed
    malformed = sum(diagnostics[kind] for kind in BAD_KINDS)
    summary = {
        "processed": processed,
        "success": success,
        "failed": failed,
        "injection_probability": BAD_RESPONSE_RATE,
        "normal": diagnostics["normal"],
        "malformed": malformed,
        "malformed_by_kind": {kind: diagnostics[kind] for kind in BAD_KINDS},
        "recovered_code_fence": diagnostics["code_fence_recovered"],
        "invalid_input": diagnostics["invalid_input"],
        "invalid_response": diagnostics["invalid_response"],
        "categories": dict(sorted(categories.items())),
    }
    if sum(categories.values()) != success or success + failed != processed:
        raise RuntimeError("집계 불변식이 맞지 않습니다.")
    return summary, outcomes


def print_summary(summary, seed):
    print("[과제 2] Mock 분류기 실행 결과")
    print(f"난수 seed: {seed if seed is not None else '미지정'}")
    print("호출별 불량 응답 주입 확률: 20% (실제 발생률은 달라질 수 있음)")
    print(f"정상 응답: {summary['normal']}건 / 불량 응답: {summary['malformed']}건")
    for kind, label in (("code_fence", "코드펜스"), ("preamble", "사족"), ("truncated", "잘린 JSON")):
        print(f"  {label}: {summary['malformed_by_kind'][kind]}건")
    print(f"코드펜스 복구: {summary['recovered_code_fence']}건")
    print(f"빈 값 등 입력 오류: {summary['invalid_input']}건")
    print(f"성공: {summary['success']}건")
    print("성공한 리뷰의 분류별 건수:")
    for category, count in summary["categories"].items():
        print(f"  {category}: {count}건")
    print(f"집계 확인: 성공 {summary['success']} + 실패 {summary['failed']} = 처리 {summary['processed']}")
    print(f"처리 {summary['processed']}건 / 실패 {summary['failed']}건")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parent / "data/reviews_sample.csv")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        reviews = load_reviews(args.input)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        parser.error(str(error))
    summary, outcomes = run_reviews(reviews, rng=random.Random(args.seed))
    summary["seed"] = args.seed
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with (args.output_dir / "row_results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("row", "status", "category", "sentiment", "score"))
            writer.writeheader()
            writer.writerows(outcomes)
    print_summary(summary, args.seed)


if __name__ == "__main__":
    main()
