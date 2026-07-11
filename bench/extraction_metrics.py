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


def format_report(scored, threshold):
    """評価結果をMarkdownの表として整形する。"""
    threshold_label = "未適用" if threshold is None else f"{threshold:.1f}"
    rows = [
        ("件数", str(scored["n"])),
        ("TP", str(scored["tp"])),
        ("FP", str(scored["fp"])),
        ("FN", str(scored["fn"])),
        ("TN", str(scored["tn"])),
        ("precision", f"{scored['precision']:.3f}"),
        ("recall", f"{scored['recall']:.3f}"),
        ("false_positive_rate", f"{scored['false_positive_rate']:.3f}"),
        ("accuracy", f"{scored['accuracy']:.3f}"),
    ]
    table = "\n".join(f"| {name} | {value} |" for name, value in rows)
    return (
        f"## confidence threshold: {threshold_label}\n\n"
        "| metric | value |\n"
        "| --- | ---: |\n"
        f"{table}\n"
    )
