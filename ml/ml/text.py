"""CrisisMMD incident text models (TF-IDF, BiLSTM, DistilBERT): train, evaluate, event-held-out folds."""

import json
import tempfile
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, recall_score
from sklearn.pipeline import make_pipeline, make_union
from sklearn.utils.class_weight import compute_class_weight
from torch import nn
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml.data import artifacts_dir, data_dir
from ml.features import clean_text

CLASSES = ["infrastructure", "affected_people", "rescue_donation", "other_relevant", "not_humanitarian"]
NOT_HUMANITARIAN = CLASSES.index("not_humanitarian")
REVIEW_SHARE = 0.15
MAX_WORDS = 48
BERT = "distilbert-base-uncased"
DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"


def softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - logits.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


class TextModel:
    """A trained classifier: cleans raw texts, scores them, returns temperature-scaled class probabilities."""

    def __init__(self, classes: list[str], temperature: float, score):
        self.classes = classes
        self.temperature = temperature
        self.score = score

    def logits(self, texts: list[str]) -> np.ndarray:
        return self.score([clean_text(text) for text in texts])

    def predict_proba(self, texts: list[str]) -> np.ndarray:
        return softmax(self.logits(texts) / self.temperature)


def load_model(path) -> TextModel:
    path = Path(path)
    meta = json.loads((path / "metadata.json").read_text())
    loader = {"tfidf": load_tfidf, "bilstm": load_bilstm, "distilbert": load_distilbert}[meta["family"]]
    return TextModel(meta["classes"], meta["temperature"], loader(path))


# --- TF-IDF + Logistic Regression ---

def fit_tfidf(texts, labels, out: Path):
    pipeline = make_pipeline(
        make_union(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True),
        ),
        LogisticRegression(class_weight="balanced", max_iter=2000),
    )
    joblib.dump(pipeline.fit(texts, labels), out / "model.joblib")


def load_tfidf(path: Path):
    return joblib.load(path / "model.joblib").decision_function


# --- BiLSTM (own vocabulary) ---

class BiLSTM(nn.Module):
    def __init__(self, vocab_size: int):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, 100, padding_idx=0)
        self.lstm = nn.LSTM(100, 64, batch_first=True, bidirectional=True)
        self.out = nn.Linear(128, len(CLASSES))

    def forward(self, ids):
        hidden, _ = self.lstm(self.embed(ids))
        mask = (ids > 0).unsqueeze(-1)
        return self.out((hidden * mask).sum(1) / mask.sum(1).clamp(min=1))


def encode_words(texts, vocab: list[str]) -> dict:
    index = {word: i for i, word in enumerate(vocab)}
    rows = [[index.get(word, 1) for word in text.split()[:MAX_WORDS]] for text in texts]
    return {"ids": torch.tensor([row + [0] * (MAX_WORDS - len(row)) for row in rows])}


def fit_bilstm(texts, labels, out: Path):
    counts = Counter(word for text in texts for word in text.split())
    vocab = ["<pad>", "<unk>"] + sorted(word for word, count in counts.items() if count >= 2)
    net = BiLSTM(len(vocab)).to(DEVICE)
    fit_torch(net, lambda batch: net(batch["ids"]), encode_words(texts, vocab), labels, 4, 2e-3, 64)
    torch.save(net.state_dict(), out / "model.pt")
    (out / "vocab.json").write_text(json.dumps(vocab))


def load_bilstm(path: Path):
    vocab = json.loads((path / "vocab.json").read_text())
    net = BiLSTM(len(vocab))
    net.load_state_dict(torch.load(path / "model.pt", map_location="cpu"))
    net.to(DEVICE).eval()
    return lambda texts: torch_logits(lambda batch: net(batch["ids"]), encode_words(texts, vocab))


# --- DistilBERT ---

def encode_bert(tokenizer, texts) -> dict:
    return dict(tokenizer(texts, truncation=True, max_length=64, padding="max_length", return_tensors="pt"))


def fit_distilbert(texts, labels, out: Path):
    tokenizer = AutoTokenizer.from_pretrained(BERT)
    net = AutoModelForSequenceClassification.from_pretrained(BERT, num_labels=len(CLASSES)).to(DEVICE)
    fit_torch(net, lambda batch: net(**batch).logits, encode_bert(tokenizer, texts), labels, 2, 5e-5, 32)
    net.save_pretrained(out)
    tokenizer.save_pretrained(out)


def load_distilbert(path: Path):
    tokenizer = AutoTokenizer.from_pretrained(path)
    net = AutoModelForSequenceClassification.from_pretrained(path).to(DEVICE).eval()
    return lambda texts: torch_logits(lambda batch: net(**batch).logits, encode_bert(tokenizer, texts))


# --- shared torch loops ---

def fit_torch(net, forward, inputs: dict, labels, epochs: int, lr: float, batch_size: int):
    """Class-weighted cross-entropy with AdamW; inputs is a dict of equally long tensors."""
    weights = compute_class_weight("balanced", classes=np.arange(len(CLASSES)), y=labels)
    loss_fn = nn.CrossEntropyLoss(weight=torch.tensor(weights, dtype=torch.float32, device=DEVICE))
    optimizer = torch.optim.AdamW(net.parameters(), lr=lr)
    targets = torch.tensor(labels)
    net.train()
    for epoch in range(epochs):
        total = 0.0
        for idx in torch.randperm(len(targets)).split(batch_size):
            loss = loss_fn(forward({k: v[idx].to(DEVICE) for k, v in inputs.items()}), targets[idx].to(DEVICE))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        print(f"  epoch {epoch + 1}/{epochs}: loss {total / len(targets):.3f}")
    net.eval()


@torch.no_grad()
def torch_logits(forward, inputs: dict, batch_size: int = 128) -> np.ndarray:
    size = len(next(iter(inputs.values())))
    parts = [forward({k: v[i:i + batch_size].to(DEVICE) for k, v in inputs.items()}) for i in range(0, size, batch_size)]
    return torch.cat(parts).float().cpu().numpy()


# --- data, training, evaluation ---

FITTERS = {"tfidf": fit_tfidf, "bilstm": fit_bilstm, "distilbert": fit_distilbert}


def load_tweets() -> pd.DataFrame:
    tweets = pd.read_parquet(data_dir() / "processed/tweets.parquet")
    tweets["label"] = tweets["category"].map(CLASSES.index)
    return tweets


def training_rows(tweets: pd.DataFrame, extra_labels=None) -> pd.DataFrame:
    """Train split minus the queue pool, plus reviewed labels (never the promotion holdout, dev or test)."""
    rows = tweets[(tweets.split == "train") & ~tweets.pool]
    if extra_labels is None:
        return rows
    extra = pd.read_parquet(extra_labels)[["tweet_id", "category"]].astype({"tweet_id": str})
    reviewed = tweets.drop(columns=["category", "label"]).merge(extra, on="tweet_id")
    reviewed = reviewed[(reviewed.split == "train") & ~reviewed.pool_holdout]
    reviewed["label"] = reviewed["category"].map(CLASSES.index)
    return pd.concat([rows[~rows.tweet_id.isin(reviewed.tweet_id)], reviewed], ignore_index=True)


def artifact_dir(family: str, version: int) -> Path:
    return artifacts_dir() / "text" / f"v{version}-{family}"


def write_metadata(out: Path, family: str, temperature: float, review_threshold: float):
    meta = {"task": "text", "family": family, "classes": CLASSES,
            "temperature": round(float(temperature), 3), "review_threshold": round(float(review_threshold), 4)}
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))


def fit_and_load(family: str, rows: pd.DataFrame, out: Path) -> TextModel:
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(0)
    FITTERS[family]([clean_text(text) for text in rows.text], rows.label.to_numpy(), out)
    write_metadata(out, family, temperature=1.0, review_threshold=0.0)
    return load_model(out)


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Grid-search the temperature that minimises dev negative log-likelihood."""
    grid = np.arange(0.25, 5.01, 0.05)
    nll = [-np.log(softmax(logits / t)[np.arange(len(labels)), labels] + 1e-12).mean() for t in grid]
    return float(grid[int(np.argmin(nll))])


def train(family: str, version: int, extra_labels=None):
    tweets = load_tweets()
    rows = training_rows(tweets, extra_labels)
    print(f"training {family} v{version} on {len(rows)} tweets ({DEVICE})")
    out = artifact_dir(family, version)
    model = fit_and_load(family, rows, out)
    dev = tweets[tweets.split == "dev"]
    logits = model.logits(dev.text.tolist())
    temperature = fit_temperature(logits, dev.label.to_numpy())
    review_threshold = np.quantile(softmax(logits / temperature).max(axis=1), REVIEW_SHARE)
    write_metadata(out, family, temperature, review_threshold)
    print(f"  temperature {temperature:.2f}, review_threshold {review_threshold:.3f}")
    return evaluate(family, version)


def score_rows(model: TextModel, rows: pd.DataFrame) -> dict:
    probs = model.predict_proba(rows.text.tolist())
    labels, predicted = rows.label.to_numpy(), probs.argmax(axis=1)
    informative = rows.informative.astype(int).to_numpy()
    screened = (1 - probs[:, NOT_HUMANITARIAN]) >= 0.5
    recalls = recall_score(labels, predicted, labels=range(len(CLASSES)), average=None, zero_division=0)
    return {
        "n": len(rows),
        "macro_f1": round(f1_score(labels, predicted, labels=range(len(CLASSES)), average="macro"), 4),
        "per_class_recall": {name: round(float(r), 4) for name, r in zip(CLASSES, recalls)},
        "confusion_matrix": confusion_matrix(labels, predicted, labels=range(len(CLASSES))).tolist(),
        "screening_f1": round(f1_score(informative, screened), 4),
        "screening_recall": round(recall_score(informative, screened), 4),
    }


def evaluate(family: str, version: int, final: bool = False) -> dict:
    """Score dev and the incident promotion holdout; the test split only when final=True."""
    out = artifact_dir(family, version)
    model = load_model(out)
    tweets = load_tweets()
    sets = {"dev": tweets.split == "dev", "pool_holdout": tweets.pool_holdout}
    if final:
        sets["test"] = tweets.split == "test"
    metrics = {name: score_rows(model, tweets[mask]) for name, mask in sets.items()}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    for name, m in metrics.items():
        print(f"{family} v{version} {name}: macro-F1 {m['macro_f1']:.3f}, "
              f"screening F1 {m['screening_f1']:.3f}, screening recall {m['screening_recall']:.3f}")
    return metrics


def leave_one_event_out(family: str) -> dict:
    """Train on all other events, score macro-F1 on the held-out event's non-test tweets."""
    if family not in ("tfidf", "bilstm"):
        raise ValueError("leave-one-event-out runs for tfidf and bilstm only")
    tweets = load_tweets()
    rows = training_rows(tweets)
    scores = {}
    for event in sorted(tweets.event.unique()):
        with tempfile.TemporaryDirectory() as tmp:
            model = fit_and_load(family, rows[rows.event != event], Path(tmp))
            scores[event] = score_rows(model, tweets[(tweets.event == event) & (tweets.split != "test")])["macro_f1"]
        print(f"  {event}: macro-F1 {scores[event]:.3f}")
    result = {"family": family, "macro_f1_by_event": scores, "mean_macro_f1": round(float(np.mean(list(scores.values()))), 4)}
    out = artifacts_dir() / "text"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"loeo-{family}.json").write_text(json.dumps(result, indent=2))
    return result


def latest_dir(family: str) -> Path:
    return max((artifacts_dir() / "text").glob(f"v*-{family}"), key=lambda path: int(path.name[1:].split("-")[0]))


def cascade_table() -> dict:
    """Offline dev table: BiLSTM screen then DistilBERT class, versus DistilBERT alone."""
    dev = load_tweets().query("split == 'dev'")
    texts, labels = dev.text.tolist(), dev.label.to_numpy()
    screened = (1 - load_model(latest_dir("bilstm")).predict_proba(texts)[:, NOT_HUMANITARIAN]) >= 0.5
    alone = load_model(latest_dir("distilbert")).predict_proba(texts).argmax(axis=1)
    pipelines = {"distilbert_alone": alone, "bilstm_screen_then_distilbert": np.where(screened, alone, NOT_HUMANITARIAN)}
    humanitarian = labels != NOT_HUMANITARIAN
    table = {"humanitarian_reports": int(humanitarian.sum())} | {
        name: {"macro_f1": round(f1_score(labels, predicted, average="macro"), 4),
               "humanitarian_suppressed": int((humanitarian & (predicted == NOT_HUMANITARIAN)).sum())}
        for name, predicted in pipelines.items()
    }
    (artifacts_dir() / "text" / "cascade.json").write_text(json.dumps(table, indent=2))
    print(json.dumps(table, indent=2))
    return table
