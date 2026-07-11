"""タスク抽出の二値分類メトリクス（純ロジック）。"""


def score(predictions, labels):
    """予測と正解からprecision、recall、誤検出率などを返す。"""
    predictions = list(predictions)
    labels = list(labels)
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")

    tp = sum(bool(prediction) and bool(label) for prediction, label in zip(predictions, labels))
    fp = sum(bool(prediction) and not bool(label) for prediction, label in zip(predictions, labels))
    fn = sum(not bool(prediction) and bool(label) for prediction, label in zip(predictions, labels))
    tn = sum(not bool(prediction) and not bool(label) for prediction, label in zip(predictions, labels))
    n = len(labels)

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "accuracy": (tp + tn) / n if n else 0.0,
        "n": n,
    }
