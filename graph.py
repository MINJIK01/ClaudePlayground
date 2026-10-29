"""docs/papers.json → docs/graph.json: 제목+abstract TF-IDF 코사인 유사도 기준 논문별 상위 graph_top_k개 이웃."""
import json, math, re, pathlib, collections

ROOT = pathlib.Path(__file__).parent
STOP = set("""a an the and or of to in on for with by from as at is are was were be been this that these those we our
it its can which via into than not but also such their they has have more both while how what when where using
based use new show shows propose proposed approach method methods paper results model models task tasks""".split())


def stem(w):
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    return w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 4 else w


def vectorize(texts):
    docs = [collections.Counter(stem(w) for w in re.findall(r"[a-z][a-z0-9-]+", t.lower()) if w not in STOP)
            for t in texts]
    df = collections.Counter(w for d in docs for w in d)
    n, vecs = len(docs), []
    for d in docs:
        v = {w: c * (math.log((1 + n) / (1 + df[w])) + 1) for w, c in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def main():
    k = json.loads((ROOT / "config.json").read_text())["graph_top_k"]
    papers = json.loads((ROOT / "docs" / "papers.json").read_text())
    vecs = vectorize(p["title"] + " " + p["abstract"] for p in papers)
    sim = lambda a, b: sum(x * b.get(w, 0.0) for w, x in a.items())
    graph = {p["id"]: sorted(([q["id"], round(sim(a, b), 3)] for q, b in zip(papers, vecs) if q is not p),
                             key=lambda e: -e[1])[:k]
             for p, a in zip(papers, vecs)}
    (ROOT / "docs" / "graph.json").write_text(json.dumps(graph))
    print(f"nodes={len(graph)}")


if __name__ == "__main__":
    main()
