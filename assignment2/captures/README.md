# 실행 화면 캡처

[run_seed42.png](run_seed42.png)는 직접 실행한 터미널 화면입니다. 다음 명령과 전체 요약을 확인할 수 있습니다.

```powershell
py -X utf8 assignment2/run_pipeline.py --seed 42 --output-dir assignment2/evidence
```

처리 200건 / 실패 25건이며, 불량 42건 중 코드펜스 17건을 복구했습니다. 저장된 실행 로그 `../evidence/run_seed42.txt` 및 집계 `../evidence/summary.json`과 일치합니다. 원본 캡처를 그대로 보존했습니다.
