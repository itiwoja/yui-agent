from bench.extraction_metrics import format_report, score


def test_score_known_predictions():
    result = score(
        predictions=[True, True, False, False, True],
        labels=[True, False, True, False, True],
    )

    assert result == {
        "tp": 2,
        "fp": 1,
        "fn": 1,
        "tn": 1,
        "precision": 2 / 3,
        "recall": 2 / 3,
        "false_positive_rate": 1 / 2,
        "accuracy": 3 / 5,
        "n": 5,
    }


def test_score_empty_input_uses_zero_for_rates():
    result = score([], [])

    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["false_positive_rate"] == 0.0
    assert result["accuracy"] == 0.0
    assert result["n"] == 0


def test_score_rejects_different_lengths():
    try:
        score([True], [])
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("ValueError was not raised")


def test_format_report_renders_metrics_as_markdown_table():
    report = format_report(
        {
            "n": 4,
            "tp": 2,
            "fp": 1,
            "fn": 0,
            "tn": 1,
            "precision": 2 / 3,
            "recall": 1.0,
            "false_positive_rate": 0.5,
            "accuracy": 0.75,
        },
        0.6,
    )

    assert "## confidence threshold: 0.6" in report
    assert "| metric | value |" in report
    assert "| false_positive_rate | 0.500 |" in report
