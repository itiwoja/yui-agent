from dataclasses import dataclass

from confidence import filter_confident


@dataclass
class Item:
    confidence: float


def test_filters_items_below_threshold():
    assert filter_confident([Item(0.59), Item(0.8)], 0.6) == [Item(0.8)]


def test_keeps_item_at_threshold():
    assert filter_confident([Item(0.6)], 0.6) == [Item(0.6)]


def test_empty_list_stays_empty():
    assert filter_confident([], 0.6) == []
