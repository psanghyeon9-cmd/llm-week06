import json
from mock_llm import mock_llm_call   # 1차시에 만든 모듈 재사용

SYSTEM = """당신은 고객 리뷰 분류기입니다.
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트를 절대 포함하지 마세요.
{"category": "배송|품질|가격|서비스|기타",
 "sentiment": "긍정|부정|중립",
 "score": 1~5 사이의 정수}"""

def classify_review(review_text):
    """리뷰 1건을 분류하여 딕셔너리로 반환. 실패 시 None."""
    result = mock_llm_call(SYSTEM, f"리뷰: {review_text}")
    raw = result["text"].strip() # 결과 텍스트의 앞뒤 불필요한 공백과 줄바꿈을 제거

    # 방어 1: 마크다운 코드 블록 제거 (포맷 정규화): ```json ... ``` 코드 제거
    if raw.startswith("```"):
        raw = raw.strip("`")  # 문자열의 시작과 끝에 붙은 백틱(`)만 모두 제거
        raw = raw.replace("json", "", 1).strip() # "json"을 한번만(1회) 지우고 strip()

    # 방어 2: 파싱 실패는 언제든 일어날 수 있다 → 예외 처리 필수
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[경고] JSON 파싱 실패: {raw[:50]}...")
        return None

    # 방어 3: 필드 존재와 값의 유효성 검증
    if data.get("category") not in ["배송", "품질", "가격", "환불", "서비스", "기타"]:
        return None
    return data

# 비즈니스 로직에 바인딩: 리뷰 목록 자동 분류 및 집계
reviews = [
    "배송이 하루 만에 왔어요 최고",
    "품질이 사진과 너무 달라요",
    "환불 처리가 왜 이렇게 느린가요",
    "상담 직원이 친절하였어요",
]
stats = {}
for r in reviews:
    result = classify_review(r)
    if result is None:          # 실패 건은 건너뛰되 기록
        continue
    cat = result["category"]
    stats[cat] = stats.get(cat, 0) + 1
print(result)
print(stats)   # 예: {'배송': 1, '품질': 1, '환불': 1} → 3주차 pandas 집계와 연결
