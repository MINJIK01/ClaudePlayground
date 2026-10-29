"""docs/papers.json → docs/graph.json: 임베딩 kNN 이웃, k-means 클러스터(+TF-IDF 라벨), 벤치마크 태그, 고정 레이아웃 좌표."""
import json, math, re, pathlib, collections
import numpy as np

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "data" / "embeddings.npz"
CENTROIDS = ROOT / "data" / "centroids.npy"
GRAPH = ROOT / "docs" / "graph.json"
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


def load_cache():
    if not CACHE.exists():
        return {}
    z = np.load(CACHE)
    return dict(zip(z["ids"].tolist(), z["vecs"]))


def save_cache(cache):
    CACHE.parent.mkdir(exist_ok=True)
    np.savez_compressed(CACHE, ids=np.array(list(cache)), vecs=np.stack(list(cache.values())))


def vectors(papers, model, cache):
    """cache에 없는 논문만 임베딩해 cache에 추가하고, 정규화된 행렬을 반환."""
    todo = [p for p in papers if p["id"] not in cache]
    if todo:
        cache.update(zip((p["id"] for p in todo), embed([p["title"] + ". " + p["abstract"] for p in todo], model)))
    if not papers:
        return np.zeros((0, 1), np.float32)
    X = np.stack([cache[p["id"]] for p in papers])
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def kmeans(X, k, C0=None, iters=100):
    """C0(이전 실행의 중심)로 시작해 클러스터 번호·색이 실행마다 유지되도록 함. 빈 클러스터는 가장 동떨어진 논문으로 재시드."""
    C0 = np.zeros((0, X.shape[1])) if C0 is None or C0.shape[1] != X.shape[1] else C0[:k]
    C = np.vstack([C0, X[np.linspace(0, len(X) - 1, k - len(C0)).astype(int)]])
    for _ in range(iters):
        lab = (X @ C.T).argmax(1)
        C2 = np.stack([X[lab == j].mean(0) if (lab == j).any() else X[(X @ C.T).max(1).argmin()] for j in range(k)])
        C2 /= np.linalg.norm(C2, axis=1, keepdims=True)
        if np.allclose(C2, C):
            break
        C = C2
    return (X @ C.T).argmax(1), C


def layout(X, edges, prev, iters=300):
    """Fruchterman-Reingold 배치. prev(이전 좌표)가 있는 논문은 그 위치에서 시작해 조금만 움직임."""
    n, rng = len(X), np.random.default_rng(0)
    I, J = np.array([e[0] for e in edges], int), np.array([e[1] for e in edges], int)
    P = rng.uniform(-0.5, 0.5, (n, 2))
    known = np.array([i in prev for i in range(n)])
    for i in range(n):
        if known[i]:
            P[i] = prev[i]
    for i in np.where(~known)[0]:  # 새 논문은 이미 배치된 가장 유사한 논문 근처에서 시작
        sims = X[known] @ X[i]
        if len(sims):
            P[i] = P[known][sims.argmax()] + rng.normal(0, 0.02, 2)
    k, t = 1 / math.sqrt(n), (0.02 if known.mean() > 0.5 else 0.1)
    for _ in range(iters):
        D = P[:, None] - P[None]
        disp = (D * (k * k / ((D ** 2).sum(-1) + 1e-6))[..., None]).sum(1)
        delta = P[I] - P[J]
        f = delta * np.linalg.norm(delta, axis=1, keepdims=True) / k
        np.add.at(disp, I, -f)
        np.add.at(disp, J, f)
        disp -= P * n * k  # 중심으로 당기는 힘 (연결 안 된 노드가 멀리 흩어지지 않게)
        step = np.linalg.norm(disp, axis=1, keepdims=True) + 1e-9
        P += disp / step * np.minimum(step, t)
        P -= P.mean(0)
        t *= 0.99
    return P


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
    ids = [p["id"] for p in papers]
    texts = [p["title"] + " " + p["abstract"] for p in papers]
    cache = load_cache()
    X = vectors(papers, cfg["embedding_model"], cache)
    save_cache({i: cache[i] for i in ids})

    S = X @ X.T
    np.fill_diagonal(S, -1)
    top = np.argsort(-S, axis=1)[:, :cfg["graph_top_k"]]
    neighbors = {ids[i]: [[ids[j], round(float(S[i, j]), 3)] for j in top[i]] for i in range(len(ids))}

    k = min(8, len(papers), max(2, round(math.sqrt(len(papers) / 2))))
    lab, C = kmeans(X, k, np.load(CENTROIDS) if CENTROIDS.exists() else None)
    np.save(CENTROIDS, C)

    old = json.loads(GRAPH.read_text()).get("pos", {}) if GRAPH.exists() else {}
    prev = {i: np.array(old[pid]) / 1000 for i, pid in enumerate(ids) if pid in old}
    P = layout(X, [(i, j) for i in range(len(ids)) for j in top[i][:3]], prev)

    pats = {name: re.compile("|".join(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])" for a in aliases))
            for name, aliases in cfg["benchmarks"].items()}
    benchmarks = {p["id"]: b for p, t in zip(papers, texts) if (b := [n for n, r in pats.items() if r.search(t)])}

    out = {"neighbors": neighbors, "cluster": {i: int(l) for i, l in zip(ids, lab)},
           "clusters": cluster_labels(texts, lab, k), "benchmarks": benchmarks,
           "pos": {i: [round(float(x) * 1000), round(float(y) * 1000)] for i, (x, y) in zip(ids, P)}}
    GRAPH.write_text(json.dumps(out))
    print(f"nodes={len(papers)} clusters={k} benchmark_tagged={len(benchmarks)} placed_before={len(prev)}")


if __name__ == "__main__":
    main()
