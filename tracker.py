"""arXiv 신규 논문 수집 → papers/YYYY-MM-DD.md 생성. 사용법: python tracker.py [lookback_days]"""
import json, sys, datetime as dt, pathlib, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).parent
NS = {"a": "http://www.w3.org/2005/Atom"}
API = "https://export.arxiv.org/api/query?"


def build_query(cfg):
    cats = " OR ".join(f"cat:{c}" for c in cfg["categories"])
    kws = " OR ".join("(" + " AND ".join(f'abs:"{w}"' for w in k) + ")" for k in cfg["keywords"])
    return f"({cats}) AND ({kws})"


def parse(xml):
    for e in ET.fromstring(xml).findall("a:entry", NS):
        text = lambda tag: " ".join(e.findtext(f"a:{tag}", "", NS).split())
        yield {
            "id": text("id").rsplit("/abs/", 1)[-1].split("v")[0],
            "url": text("id"),
            "title": text("title"),
            "abstract": text("summary"),
            "published": text("published")[:10],
            "authors": [a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)],
            "cats": [c.get("term") for c in e.findall("a:category", NS)],
        }


def matched(p, cfg):
    hay = (p["title"] + " " + p["abstract"]).lower()
    return [" + ".join(k) for k in cfg["keywords"] if all(w in hay for w in k)]


def to_md(p, cfg):
    authors = ", ".join(p["authors"][:5]) + (" et al." if len(p["authors"]) > 5 else "")
    return (f"### [{p['title']}]({p['url']})\n"
            f"- {authors}\n- {p['published']} · {', '.join(p['cats'])} · 매칭: {', '.join(matched(p, cfg))}\n\n"
            f"<details><summary>Abstract</summary>\n\n{p['abstract']}\n</details>\n")


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    days = int(sys.argv[1]) if len(sys.argv) > 1 else cfg["lookback_days"]
    seen_path = ROOT / "seen.json"
    seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()

    params = {"search_query": build_query(cfg), "sortBy": "submittedDate",
              "sortOrder": "descending", "max_results": cfg["max_results"]}
    with urllib.request.urlopen(API + urllib.parse.urlencode(params), timeout=60) as r:
        papers = list(parse(r.read()))

    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    new = [p for p in papers if p["published"] >= cutoff and p["id"] not in seen and matched(p, cfg)]
    print(f"fetched={len(papers)} new={len(new)}")
    if not new:
        return

    out = ROOT / "papers" / f"{dt.date.today()}.md"
    out.parent.mkdir(exist_ok=True)
    head = "" if out.exists() else f"# {dt.date.today()}\n\n"
    with out.open("a") as f:
        f.write(head + "\n".join(to_md(p, cfg) for p in new))
    seen_path.write_text(json.dumps(sorted(seen | {p["id"] for p in new}), indent=0))


if __name__ == "__main__":
    main()
