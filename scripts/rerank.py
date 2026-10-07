from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(question, candidates, top_k=5):
    """Reclasse les chunks candidats avec un Cross-Encoder.

    candidates: liste de tuples (content, source, page, similarity)
    retourne: les top_k candidats réordonnés selon le score du Cross-Encoder
    """
    if not candidates:
        return []

    pairs = [[question, c[0]] for c in candidates]
    scores = reranker.predict(pairs)
    scored_candidates = list(zip(scores, candidates))
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    return [candidate for _, candidate in scored_candidates[:top_k]]
