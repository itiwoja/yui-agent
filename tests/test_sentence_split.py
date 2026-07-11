from sentence_split import split_sentences


def test_split_sentences_returns_complete_sentences_and_remainder():
    ready, remainder = split_sentences("これは最初の文です。次は途中")

    assert ready == ["これは最初の文です。"]
    assert remainder == "次は途中"


def test_split_sentences_combines_short_acknowledgements():
    ready, remainder = split_sentences("はい。了解しました。")

    assert ready == ["はい。了解しました。"]
    assert remainder == ""


def test_split_sentences_keeps_short_complete_text_for_later():
    ready, remainder = split_sentences("はい。")

    assert ready == []
    assert remainder == "はい。"
