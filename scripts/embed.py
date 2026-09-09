from sentence_transformers import SentenceTransformer
from chunk import load_pdf

model = SentenceTransformer("BAAI/bge-small-en-v1.5")


def embed_texts(texts, model):
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return vecs



if __name__ == "__main__":
    docs = load_pdf("data/p538.pdf")
    texts = [d["content"] for d in docs]
    vecs = embed_texts(texts, model)
    print(vecs.shape)

    question = "Represent this sentence for searching relevant passages: What is a fiscal year?"
    qvec = model.encode([question], normalize_embeddings=True)[0]

    sims = vecs @ qvec                      # 70 similarités d'un coup
    top = sims.argsort()[::-1][:3]          # les 3 meilleurs indices

    for i in top:
        print(round(float(sims[i]), 3), "| page", docs[i]["page"], "|", docs[i]["content"][:150])