import json
from pathlib import Path

import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

from services.embedding import get_embedding_model

N_CLUSTERS = 4


def embed_tweets(tweets: list[dict], model=None):
    model = model or get_embedding_model()
    texts = [t["text"] for t in tweets]
    return model.encode(texts)


def cluster_embeddings(embeddings, n_clusters: int = N_CLUSTERS):
    n_clusters = min(n_clusters, len(embeddings))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    return labels


def plot_clusters(embeddings, labels, out_path: Path = None):
    if out_path is None:
        import config
        out_path = config.DATA_DIR / "cluster_plot.png"
    coords = PCA(n_components=2, random_state=42).fit_transform(embeddings)
    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=labels, cmap="tab10")
    plt.title("Tweet style clusters (PCA projection)")
    plt.colorbar(scatter, label="cluster")
    plt.savefig(out_path)
    plt.close()


def main():
    import sys
    from pathlib import Path as P
    if __package__ is None:
        sys.path.insert(0, str(P(__file__).parent.parent))
    import config

    with open(config.DATA_DIR / "clean_tweets.json", encoding="utf-8") as f:
        tweets = json.load(f)

    embeddings = embed_tweets(tweets)
    labels = cluster_embeddings(embeddings)

    for tweet, embedding, label in zip(tweets, embeddings, labels):
        tweet["cluster"] = int(label)
        tweet["embedding"] = embedding.tolist()

    out_path = config.DATA_DIR / "tweets_with_clusters.json"
    out_path.write_text(json.dumps(tweets, indent=2), encoding="utf-8")
    plot_clusters(embeddings, labels)
    print(f"Embedded + clustered {len(tweets)} tweets into {len(set(labels))} clusters")


if __name__ == "__main__":
    main()
