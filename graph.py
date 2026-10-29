"""docs/papers.json → docs/graph.json: 임베딩 kNN 이웃, k-means 클러스터(+TF-IDF 라벨), 벤치마크 태그."""
import json, math, re, pathlib, collections
import numpy as np

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "data" / "embeddings.npz"
STOP = set("""a an the and or of to in on for with by from as at is are was were be been this that these those we our
it its can which via into than not but also such their they has have more both while how what when where using
based use new show shows propose proposed approach method methods paper results model models task tasks""".split())


def stem(w):
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    return w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 4 else w


def tfidf(texts):
    docs = [collections.Counter(stem(w) for w in re.findall(r"[a-z][a-z0-9-]+", t.lower()) if w not in STOP)
            for t in texts]
    df = collections.Counter(w for d in docs for w in d)
    vecs = []
    for d in docs:
        v = {w: c * (math.log((1 + len(docs)) / (1 + df[w])) + 1) for w, c in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    return vecs


def embed(texts, model):
    from fastembed import TextEmbedding
    return np.array(list(TextEmbedding(model, cache_dir=str(ROOT / ".cache" / "fastembed")).embed(texts)), dtype=np.float32)


def embeddings(papers, model):
    """새 논문만 임베딩하고 data/embeddings.npz에 누적 캐시."""
    cache = {}
    if CACHE.exists():
        z = np.load(CACHE)
        cache = dict(zip(z["ids"].tolist(), z["vecs"]))
    todo = [p for p in papers if p["id"] not in cache]
    if todo:
        cache.update(zip((p["id"] for p in todo), embed([p["title"] + ". " + p["abstract"] for p in todo], model)))
        CACHE.parent.mkdir(exist_ok=True)
        np.savez_compressed(CACHE, ids=np.array(list(cache)), vecs=np.stack(list(cache.values())))
    X = np.stack([cache[p["id"]] for p in papers])
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def kmeans(X, k, iters=100):
    C = X[np.linspace(0, len(X) - 1, k).astype(int)]
    for _ in range(iters):
        lab = (X @ C.T).argmax(1)
        C2 = np.stack([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
        C2 /= np.linalg.norm(C2, axis=1, keepdims=True)
        if np.allclose(C2, C):
            break
        C = C2
    return lab


def cluster_labels(texts, lab, k, n=3):
    vecs = tfidf(texts)
    total = collections.Counter()
    for v in vecs:
        total.update(v)
    labels = []
    for j in range(k):
        members = [v for v, l in zip(vecs, lab) if l == j]
        inside, df = collections.Counter(), collections.Counter()
        for v in members:
            inside.update(v)
            df.update(v.keys())
        # 클러스터 내 2편 이상에 나오는 단어 중, 전체 평균 대비 비중이 큰 단어 (논문 고유 이름 배제)
        score = {w: inside[w] / len(members) - total[w] / len(vecs) for w in inside if df[w] >= min(2, len(members))}
        labels.append(sorted(score, key=score.get, reverse=True)[:n])
    return labels


def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    papers = json.loads((ROOT / "docs" / "papers.json").read_text())
    texts = [p["title"] + " " + p["abstract"] for p in papers]
    X = embeddings(papers, cfg["embedding_model"])

    S = X @ X.T
    np.fill_diagonal(S, -1)
    top = np.argsort(-S, axis=1)[:, :cfg["graph_top_k"]]
    neighbors = {p["id"]: [[papers[j]["id"], round(float(S[i, j]), 3)] for j in top[i]] for i, p in enumerate(papers)}

    k = min(8, len(papers), max(2, round(math.sqrt(len(papers) / 2))))
    lab = np.unique(kmeans(X, k), return_inverse=True)[1]  # 빈 클러스터 제거 후 0..k-1로 재번호
    k = int(lab.max()) + 1
    pats = {name: re.compile("|".join(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])" for a in aliases))
            for name, aliases in cfg["benchmarks"].items()}
    benchmarks = {p["id"]: b for p, t in zip(papers, texts) if (b := [n for n, r in pats.items() if r.search(t)])}

    out = {"neighbors": neighbors, "cluster": {p["id"]: int(l) for p, l in zip(papers, lab)},
           "clusters": cluster_labels(texts, lab, k), "benchmarks": benchmarks}
    (ROOT / "docs" / "graph.json").write_text(json.dumps(out))
    print(f"nodes={len(papers)} clusters={k} benchmark_tagged={len(benchmarks)}")


if __name__ == "__main__":
    main()
