# arXiv Paper Tracker

`config.json`의 카테고리·키워드로 arXiv 신규 논문을 평일마다 자동 수집해 `papers/YYYY-MM-DD.md`로 커밋합니다. 외부 의존성과 API 키는 필요 없습니다.
Collects new arXiv papers matching the categories and keywords in `config.json` every weekday and commits them to `papers/YYYY-MM-DD.md`. No external dependencies or API keys are required.

**Paper graph / 논문 그래프:** https://minjik01.github.io/Memory-paper-Memory/

## 설정 / Configuration (`config.json`)
| Key | 설명 | Description |
|---|---|---|
| `categories` | arXiv 카테고리. 주 카테고리(primary)가 이 목록에 있는 논문만 저장 | arXiv categories. Only papers whose primary category is listed are kept |
| `keywords` | 각 항목은 제목·abstract 내 AND 조건, 항목끼리는 OR | Each entry is an AND of terms in the title/abstract; entries are OR-ed |
| `lookback_days` | 수집 대상 기간 (제출일 기준) | Collection window in days (by submission date) |
| `max_results` | arXiv API 1회 조회 상한 | Maximum results per arXiv API request |
| `graph_top_k` | 그래프에서 논문별로 저장할 유사 논문 수 | Number of similar papers stored per paper for the graph |

수집한 논문은 `docs/papers.json`에 누적되며 중복 수집되지 않습니다.
Collected papers accumulate in `docs/papers.json` and are never collected twice.

## 실행 / Running
- 자동 / Scheduled: 평일 02:23 UTC (`.github/workflows/track.yml`) / weekdays at 02:23 UTC
- 수동 / Manual: Actions → arXiv tracker → Run workflow (`days`로 과거 기간 백필 / backfill with `days`)
- 로컬 / Local: `python tracker.py [days] && python graph.py`

## 논문 그래프 / Paper graph
`graph.py`가 제목+abstract의 TF-IDF 코사인 유사도로 논문별 상위 k개 유사 논문을 계산해 `docs/graph.json`에 저장하고, `docs/index.html`이 이를 인터랙티브 그래프로 보여줍니다.
`graph.py` computes each paper's top-k most similar papers by TF-IDF cosine similarity over title and abstract and writes them to `docs/graph.json`; `docs/index.html` renders them as an interactive graph.

- 논문당 연결 수 1–5 선택 / Choose 1–5 links per paper
- 키워드 칩으로 그룹 표시·숨김 / Toggle keyword groups with the chips
- 노드 클릭 시 abstract와 유사 논문 목록 / Select a node to see its abstract and most similar papers
- GitHub Pages 설정 / Pages setup: Settings → Pages → Branch `main` / `/docs`

## 요약 / Summaries
Claude Code 세션에서 "papers/ 이번 주 논문 요약해줘"처럼 요청하면 요약할 수 있습니다.
Ask a Claude Code session, for example "summarize this week's papers in papers/", to get summaries.
