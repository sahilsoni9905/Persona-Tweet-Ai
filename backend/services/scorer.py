import json
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

import config
from services.embedding import get_embedding_model

CLEAN_PATH = config.DATA_DIR / "clean_tweets.json"
MODEL_PATH = config.DATA_DIR / "style_classifier.joblib"
METRICS_PATH = config.DATA_DIR / "scorer_metrics.json"

NEGATIVE_EXAMPLES = [
    "We are pleased to announce a new strategic partnership to drive synergies.",
    "Our team is committed to delivering best-in-class solutions for our stakeholders.",
    "Thank you for reaching out, please find the attached document for your reference.",
    "This quarter's results reflect our ongoing commitment to operational excellence.",
    "We value your feedback and are continuously working to improve our services.",
    "Please be advised that scheduled maintenance will occur on the specified date.",
    "Our mission is to leverage innovative technology to create long-term value.",
    "We appreciate your patience as we resolve this issue as quickly as possible.",
    "The following report outlines key performance indicators for the fiscal year.",
    "In accordance with company policy, all requests must be submitted in writing.",
    "We are excited to share updates regarding our upcoming product roadmap.",
    "This message is to confirm receipt of your recent inquiry.",
    "Our customer support team is available to assist with any questions you may have.",
    "We remain focused on delivering shareholder value through disciplined execution.",
    "Kindly review the attached terms and conditions before proceeding.",
    "The meeting has been rescheduled to accommodate all relevant stakeholders.",
    "We are dedicated to fostering an inclusive and collaborative work environment.",
    "Please do not hesitate to contact us should you require further assistance.",
    "This update includes several enhancements aimed at improving user experience.",
    "Our organization prioritizes compliance with all applicable regulations.",
    "We look forward to continuing our partnership in the years ahead.",
    "The annual report provides a comprehensive overview of our financial performance.",
    "We are committed to transparency and accountability in all our operations.",
    "Please find below a summary of the action items discussed during the call.",
    "Our goal is to provide a seamless and efficient experience for all users.",
]


def load_positive_texts(path: Path = CLEAN_PATH) -> list[str]:
    with open(path, encoding="utf-8") as f:
        tweets = json.load(f)
    texts = [t["text"] for t in tweets]
    try:
        from services.style_index import _collection
        manual = _collection.get(where={"source": "manual"})
        texts += manual["documents"]
    except Exception:
        pass
    return texts


def train():
    model = get_embedding_model()
    positives = load_positive_texts()
    negatives = NEGATIVE_EXAMPLES

    texts = positives + negatives
    labels = [1] * len(positives) + [0] * len(negatives)
    embeddings = model.encode(texts)

    X_train, X_test, y_train, y_test = train_test_split(
        embeddings, labels, test_size=0.3, random_state=42, stratify=labels
    )

    classifier = LogisticRegression(max_iter=1000)
    classifier.fit(X_train, y_train)
    y_pred = classifier.predict(X_test)

    metrics = {
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
    }

    joblib.dump(classifier, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def score_candidates(texts: list[str]) -> list[float]:
    classifier = joblib.load(MODEL_PATH)
    model = get_embedding_model()
    embeddings = model.encode(texts)
    return classifier.predict_proba(embeddings)[:, 1].tolist()


def main():
    import sys
    from pathlib import Path as P
    if __package__ is None:
        sys.path.insert(0, str(P(__file__).parent.parent))
    metrics = train()
    print(f"precision={metrics['precision']:.3f} recall={metrics['recall']:.3f} f1={metrics['f1']:.3f}")


if __name__ == "__main__":
    main()
