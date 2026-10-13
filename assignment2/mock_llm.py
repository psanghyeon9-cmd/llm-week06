"""수업의 고정 응답을 유지하면서 형식 오류를 주입하는 Mock입니다."""

import random

BAD_RESPONSE_RATE = 0.20
BAD_KINDS = ("code_fence", "preamble", "truncated")


def mock_llm_call(system, user_message, temperature=0.2, max_tokens=500, *, rng=None):
    generator = rng if rng is not None else random
    reviews_keywords = {
        "배송": '{"category": "배송", "sentiment": "긍정", "score": 4}',
        "환불": '{"category": "환불", "sentiment": "부정", "score": 2}',
        "품질": '{"category": "품질", "sentiment": "긍정", "score": 5}',
    }
    text = '{"category": "기타", "sentiment": "중립", "score": 3}'
    for keyword, canned in reviews_keywords.items():
        if keyword in user_message:
            text = canned
            break

    kind = "normal"
    if generator.random() < BAD_RESPONSE_RATE:
        kind = generator.choice(BAD_KINDS)
        if kind == "code_fence":
            text = "```json\n" + text + "\n```"
        elif kind == "preamble":
            text = "물론입니다! 분석 결과는 다음과 같습니다. " + text
        else:
            text = text[:len(text) // 2]

    return {
        "text": text,
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 120, "output_tokens": 35},
        "mock_response_kind": kind,
    }
