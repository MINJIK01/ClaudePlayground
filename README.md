# arXiv Paper Tracker

`config.json`의 카테고리·키워드로 arXiv 신규 논문을 평일마다 자동 수집해 `papers/YYYY-MM-DD.md`로 커밋합니다. 외부 의존성과 API 키는 필요 없습니다.

## 설정 (`config.json`)
- `categories`: arXiv 카테고리 (OR). 주 카테고리(primary)가 이 목록에 있는 논문만 저장됩니다.
- `keywords`: 리스트의 각 항목은 abstract 내 AND 조건이고, 항목끼리는 OR로 결합됩니다.
- `lookback_days`: 수집 대상 기간 (제출일 기준)
- 이미 수집한 논문 ID는 `seen.json`에 저장되며, 중복 수집되지 않습니다.

## 실행
- 자동: 평일 02:23 UTC (`.github/workflows/track.yml`). 스케줄은 이 워크플로가 default branch에 있어야 동작합니다.
- 수동: Actions → arXiv tracker → Run workflow (`days`로 과거 기간 백필)
- 로컬: `python tracker.py [days]`

## 요약
Claude Code 세션에서 "papers/ 이번 주 논문 요약해줘"처럼 요청하면 요약할 수 있습니다.
