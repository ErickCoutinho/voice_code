"""Síntese de voz (edge-tts) e reprodução interrompível pela voz do usuário."""

import asyncio
import contextlib
import io
import logging
import threading
import time
from collections.abc import Callable, Iterator

import edge_tts
import numpy as np
import sounddevice as sd
import soundfile as sf

logger = logging.getLogger(__name__)

MIC_SAMPLE_RATE = 16_000
MIC_BLOCK_SIZE = 1_600  # 100 ms por bloco.
VOICE_BLOCKS_TO_INTERRUPT = 3  # Cerca de 300 ms de voz contínua.
POLL_INTERVAL_SECONDS = 0.05
SILENCE_AMPLITUDE = 0.01
# O edge-tts acrescenta cerca de 0,7 s de silêncio ao fim de cada áudio, o que
# deixa pausas longas entre frases. Mantém só uma pausa natural.
KEPT_LEADING_SILENCE_SECONDS = 0.05
KEPT_TRAILING_SILENCE_SECONDS = 0.2


class VoiceDetector:
    """Detecta voz no microfone por volume (RMS) sustentado."""

    def __init__(self, threshold: float) -> None:
        self._threshold = threshold
        self._consecutive_loud_blocks = 0
        self.voice_detected = threading.Event()

    def on_audio(self, data: np.ndarray, _frames: int, _time: object, _status: sd.CallbackFlags) -> None:
        """Callback do sounddevice: marca voz após blocos altos consecutivos."""
        if rms_level(data) >= self._threshold:
            self._consecutive_loud_blocks += 1
        else:
            self._consecutive_loud_blocks = 0
        if self._consecutive_loud_blocks >= VOICE_BLOCKS_TO_INTERRUPT:
            self.voice_detected.set()


def rms_level(data: np.ndarray) -> float:
    """Volume médio (RMS) de um bloco de áudio em float32, entre 0 e 1."""
    return float(np.sqrt(np.mean(np.square(data))))


async def speak_sentences(
    sentences: list[str],
    voice: str,
    rate: str,
    interrupt_threshold: float,
    should_continue: Callable[[], bool],
) -> None:
    """Fala as frases em ordem, sintetizando a próxima enquanto a atual toca.

    Para ao fim das frases, ao detectar voz no microfone ou quando
    should_continue retornar False.
    """
    if not sentences:
        return
    detector = VoiceDetector(interrupt_threshold)

    def keep_playing() -> bool:
        """A fala continua enquanto não for cancelada nem interrompida pela voz."""
        return should_continue() and not detector.voice_detected.is_set()

    with _listening_microphone(detector):
        next_audio = asyncio.create_task(_synthesize(sentences[0], voice, rate))
        try:
            for index in range(len(sentences)):
                mp3_bytes = await next_audio
                if index + 1 < len(sentences):
                    next_audio = asyncio.create_task(_synthesize(sentences[index + 1], voice, rate))
                if not keep_playing():
                    break
                samples, sample_rate = _decode_mp3(mp3_bytes)
                samples = trim_silence(samples, sample_rate)
                if samples.size:
                    await asyncio.to_thread(_play_until, samples, sample_rate, keep_playing)
        finally:
            next_audio.cancel()

    if detector.voice_detected.is_set():
        logger.info("Fala interrompida pela voz do usuário.")


@contextlib.contextmanager
def _listening_microphone(detector: VoiceDetector) -> Iterator[None]:
    """Mantém o microfone alimentando o detector enquanto o bloco estiver ativo."""
    try:
        microphone = sd.InputStream(
            samplerate=MIC_SAMPLE_RATE,
            blocksize=MIC_BLOCK_SIZE,
            channels=1,
            dtype="float32",
            callback=detector.on_audio,
        )
    except sd.PortAudioError:
        # Sem microfone a fala continua, apenas sem interrupção por voz.
        logger.warning("Microfone indisponível; a fala não poderá ser interrompida pela voz.", exc_info=True)
        yield
        return
    with microphone:
        yield


async def _synthesize(text: str, voice: str, rate: str) -> bytes:
    """Converte o texto em áudio MP3 pelo serviço do edge-tts."""
    buffer = bytearray()
    async for chunk in edge_tts.Communicate(text, voice, rate=rate).stream():
        if chunk["type"] == "audio":
            buffer.extend(chunk["data"])
    return bytes(buffer)


def _decode_mp3(mp3_bytes: bytes) -> tuple[np.ndarray, int]:
    """Decodifica o MP3 em amostras float32 e retorna também a taxa de amostragem."""
    samples, sample_rate = sf.read(io.BytesIO(mp3_bytes), dtype="float32")
    return samples, sample_rate


def trim_silence(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Corta o silêncio das pontas, mantendo pausas curtas antes e depois da fala."""
    audible = np.flatnonzero(np.abs(samples) > SILENCE_AMPLITUDE)
    if audible.size == 0:
        return samples[:0]
    start = max(0, audible[0] - int(KEPT_LEADING_SILENCE_SECONDS * sample_rate))
    end = min(len(samples), audible[-1] + 1 + int(KEPT_TRAILING_SILENCE_SECONDS * sample_rate))
    return samples[start:end]


def _play_until(samples: np.ndarray, sample_rate: int, should_continue: Callable[[], bool]) -> None:
    """Toca o áudio e bloqueia até o fim ou até should_continue retornar False."""
    sd.play(samples, sample_rate)
    try:
        while sd.get_stream().active:
            if not should_continue():
                return
            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        sd.stop()
