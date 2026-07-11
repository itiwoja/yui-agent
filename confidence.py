"""抽出confidenceのしきい値判定（純ロジック）。"""


def filter_confident(items, threshold, get=lambda item: item.confidence):
    """confidence が threshold 以上の要素だけ返す。"""
    return [item for item in items if get(item) >= threshold]
