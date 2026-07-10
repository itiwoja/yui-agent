"""Google Cloud Speech-to-Textで音声メモをまとめて文字起こしする。

逐次(ストリーミング)ではなく、録音済みの音声全体を一括で認識する。
文脈を保ったまま解釈させることで、意図通りの文字起こしを狙う。
"""
from google.cloud import speech

_client = None

# 認識されやすいよう重みづけするフレーズ。呼びかけ語(ゆい)を最優先で拾う。
PHRASE_HINTS = [
    "ゆい", "ユイ",
    "タスク", "締め切り", "期限", "資料", "会議", "申告", "支払い", "確認",
]


def _get_client() -> speech.SpeechClient:
    global _client
    if _client is None:
        _client = speech.SpeechClient()
    return _client


def transcribe_audio(audio_bytes: bytes) -> str:
    client = _get_client()
    response = client.recognize(
        config=speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            language_code="ja-JP",
            enable_automatic_punctuation=True,
            model="latest_long",
            use_enhanced=True,
            speech_contexts=[
                speech.SpeechContext(phrases=PHRASE_HINTS, boost=15.0),
            ],
        ),
        audio=speech.RecognitionAudio(content=audio_bytes),
    )
    return "".join(
        result.alternatives[0].transcript
        for result in response.results
        if result.alternatives
    )
