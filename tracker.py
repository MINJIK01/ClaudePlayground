"""arXiv 신규 논문 수집 → papers/YYYY-MM-DD.md, docs/papers.json(누적) 갱신. 사용법: python tracker.py [lookback_days]"""
import json, sys, datetime as dt, pathlib, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).parent
NS = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
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
            "primary": e.find("x:primary_category", NS).get("term"),
        }


def matched(p, cfg):
    hay = (p["title"] + " " + p["abstract"]).lower()
    return [" + ".join(k) for k in cfg["keywords"] if all(w in hay for w in k)]


def to_md(p, cfg):
    authors = ", ".join(p["authors"][:5]) + (" et al." if len(p["authors"]) > 5 else "")
    return (f"### [{p['title']}]({p['url']})\n"
            f"- {authors}\n- {p['published']} · {', '.join(p['cats'])} · Matched: {', '.join(matched(p, cfg))}\n\n"
            f"<details><summary>Abstract</summary>\n\n{p['abstract']}\n</details>\n")


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    days = int(sys.argv[1]) if len(sys.argv) > 1 else cfg["lookback_days"]
    db_path = ROOT / "docs" / "papers.json"
    db = json.loads(db_path.read_text()) if db_path.exists() else []
    seen = {p["id"] for p in db}

    params = {"search_query": build_query(cfg), "sortBy": "submittedDate",
              "sortOrder": "descending", "max_results": cfg["max_results"]}
    with urllib.request.urlopen(API + urllib.parse.urlencode(params), timeout=60) as r:
        papers = list(parse(r.read()))

    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    new = [p for p in papers if p["published"] >= cutoff and p["id"] not in seen
           and p["primary"] in cfg["categories"] and matched(p, cfg)]
    print(f"fetched={len(papers)} new={len(new)}")
    if not new:
        return

    out = ROOT / "papers" / f"{dt.date.today()}.md"
    out.parent.mkdir(exist_ok=True)
    head = "" if out.exists() else f"# {dt.date.today()}\n\n"
    with out.open("a") as f:
        f.write(head + "\n".join(to_md(p, cfg) for p in new))
    for p in new:
        p["matched"] = matched(p, cfg)
    db_path.write_text(json.dumps(db + new, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
