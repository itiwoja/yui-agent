"""Incrementally split model output into natural speech-sized sentences."""

from __future__ import annotations


_SENTENCE_ENDINGS = frozenset("。！？!?\n")
_MIN_SPEECH_CHARS = 6


def split_sentences(buffer: str) -> tuple[list[str], str]:
    """Return complete, speakable sentences and an unfinished remainder.

    Short acknowledgements are kept until the next complete sentence so that the
    text-to-speech service is not invoked for unnaturally tiny fragments.
    """
    ready: list[str] = []
    pending = ""
    start = 0

    for index, character in enumerate(buffer):
        if character not in _SENTENCE_ENDINGS:
            continue
        sentence = buffer[start : index + 1]
        start = index + 1
        if not sentence.strip():
            continue
        pending += sentence
        if len(pending.strip()) >= _MIN_SPEECH_CHARS:
            ready.append(pending.strip())
            pending = ""

    return ready, pending + buffer[start:]
