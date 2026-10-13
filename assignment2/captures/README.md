# 실행 화면 캡처 대기

VS Code에서 다음 명령을 실행하고 명령과 요약 출력이 보이는 실제 화면을 `run_seed42.png`로 저장합니다.

```powershell
py -X utf8 assignment2/run_pipeline.py --seed 42 --output-dir assignment2/evidence
```

예상 최종 줄은 `처리 200건 / 실패 25건`입니다. 실제 실행 로그는 `../evidence/run_seed42.txt`에 저장되어 있습니다. 로그와 화면 캡처는 구분합니다.
