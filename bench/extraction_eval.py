"""実Geminiで独り言サンプルの抽出精度を手動評価する。"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench.extraction_metrics import format_report, score  # noqa: E402
from confidence import filter_confident  # noqa: E402
from extraction import extract_tasks  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="実Geminiによるタスク抽出評価")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="confidenceしきい値（既定: 0.6）",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="0.0, 0.3, 0.5, 0.6, 0.7, 0.8 のしきい値を比較する",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Markdownレポートの出力先（例: bench/results/extraction-eval.md）",
    )
    args = parser.parse_args()

    samples_path = Path(__file__).with_name("extraction_samples.json")
    samples = json.loads(samples_path.read_text(encoding="utf-8"))
    predictions = []
    task_groups = []
    labels = []

    for sample in samples:
        result = extract_tasks(sample["utterance"])
        predictions.append(bool(result.tasks))
        task_groups.append(result.tasks)
        labels.append(sample["expect"] == "task")
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

    thresholds = [0.0, 0.3, 0.5, 0.6, 0.7, 0.8] if args.sweep else [args.threshold]
    raw_score = score(predictions, labels)
    report_sections = ["# タスク抽出評価\n", format_report(raw_score, None)]
    threshold_scores = []

    print("raw:", json.dumps(raw_score, ensure_ascii=False, indent=2))
    for threshold in thresholds:
        filtered_score = score(
            [bool(filter_confident(tasks, threshold)) for tasks in task_groups], labels
        )
        print(
            f"threshold={threshold}:",
            json.dumps(filtered_score, ensure_ascii=False, indent=2),
        )
        threshold_scores.append((threshold, filtered_score))
        report_sections.append(format_report(filtered_score, threshold))

    if args.sweep:
        sweep_rows = [
            "| threshold | precision | recall | false_positive_rate | accuracy |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
        sweep_rows.extend(
            (
                "| {threshold:.1f} | {precision:.3f} | {recall:.3f} | "
                "{false_positive_rate:.3f} | {accuracy:.3f} |"
            ).format(
                threshold=threshold,
                **scored,
            )
            for threshold, scored in threshold_scores
        )
        report_sections.insert(2, "## しきい値スイープ\n\n" + "\n".join(sweep_rows))

    report = "\n".join(report_sections)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"report: {args.out}")


if __name__ == "__main__":
    main()
