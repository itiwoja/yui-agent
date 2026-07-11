"""実Geminiで独り言サンプルの抽出精度を手動評価する。"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.extraction_metrics import score  # noqa: E402
from confidence import filter_confident  # noqa: E402
from extraction import extract_tasks  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="実Geminiによるタスク抽出評価")
    parser.add_argument(
        "--threshold",
        type=float,
        help="指定時はconfidenceしきい値適用後のメトリクスも表示する",
    )
    args = parser.parse_args()

    samples_path = Path(__file__).with_name("extraction_samples.json")
    samples = json.loads(samples_path.read_text(encoding="utf-8"))
    predictions = []
    filtered_predictions = []
    labels = []

    for sample in samples:
        result = extract_tasks(sample["utterance"])
        predictions.append(bool(result.tasks))
        labels.append(sample["expect"] == "task")
        if args.threshold is not None:
            filtered_predictions.append(
                bool(filter_confident(result.tasks, args.threshold))
            )
        print(
            json.dumps(
                {
                    "utterance": sample["utterance"],
                    "expect": sample["expect"],
                    "tasks": [task.model_dump() for task in result.tasks],
                },
                ensure_ascii=False,
            )
        )

    print("raw:", json.dumps(score(predictions, labels), ensure_ascii=False, indent=2))
    if args.threshold is not None:
        print(
            f"threshold={args.threshold}:",
            json.dumps(score(filtered_predictions, labels), ensure_ascii=False, indent=2),
        )


if __name__ == "__main__":
    main()
