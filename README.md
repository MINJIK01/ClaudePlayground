# arXiv Paper Tracker

`config.json`의 카테고리·키워드로 arXiv 신규 논문을 평일마다 자동 수집해 `papers/YYYY-MM-DD.md`로 커밋합니다. 외부 의존성과 API 키는 필요 없습니다.

## 설정 (`config.json`)
- `categories`: arXiv 카테고리 (OR). 주 카테고리(primary)가 이 목록에 있는 논문만 저장됩니다.
- `keywords`: 리스트의 각 항목은 abstract 내 AND 조건이고, 항목끼리는 OR로 결합됩니다.
- `lookback_days`: 수집 대상 기간 (제출일 기준)
- `graph_top_k`: 그래프에서 논문별로 저장할 유사 논문 수
- 수집한 논문은 `docs/papers.json`에 누적되며, 중복 수집되지 않습니다.

## 실행
- 자동: 평일 02:23 UTC (`.github/workflows/track.yml`). 스케줄은 이 워크플로가 default branch에 있어야 동작합니다.
- 수동: Actions → arXiv tracker → Run workflow (`days`로 과거 기간 백필)
- 로컬: `python tracker.py [days]`

## 논문 그래프
`graph.py`가 제목+abstract의 TF-IDF 코사인 유사도로 논문별 상위 k개 유사 논문을 계산해 `docs/graph.json`에 저장하고, `docs/index.html`이 이를 인터랙티브 그래프로 보여줍니다 (GitHub Pages: Settings → Pages → Branch `main` / `docs`).
- 슬라이더: 논문당 표시할 연결 수 (1–5)
- 노드 클릭: 논문 정보와 유사 논문 Top-k, 노드 색: 매칭 키워드

## 요약
Claude Code 세션에서 "papers/ 이번 주 논문 요약해줘"처럼 요청하면 요약할 수 있습니다.
