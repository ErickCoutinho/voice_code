import numpy as np

from voice_code.audio_output import trim_silence

SAMPLE_RATE = 1_000


def test_trim_silence_keeps_short_pauses_around_speech():
    speech = np.full(500, 0.5, dtype=np.float32)
    samples = np.concatenate([np.zeros(300), speech, np.zeros(700)]).astype(np.float32)

    trimmed = trim_silence(samples, SAMPLE_RATE)

    # 50 ms antes e 200 ms depois da fala, a 1 kHz.
    assert len(trimmed) == 50 + 500 + 200


def test_trim_silence_of_silent_audio_returns_empty():
    assert trim_silence(np.zeros(1_000, dtype=np.float32), SAMPLE_RATE).size == 0
