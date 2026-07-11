from bench.extraction_metrics import score


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
