"""
Real-time audio pipeline for WebSocket / WebRTC callers.

Honesty note: Groq's Whisper endpoint is a batch (not token-streaming) API —
there is no true incremental ASR here. "Real-time" is achieved by buffering
incoming PCM/webm audio into short rolling windows (~settings.stream_chunk_seconds)
and re-transcribing each window as it fills, which is the standard approach
used by most voice-agent stacks built on top of a batch Whisper endpoint.
An utterance is considered finished after a silence gap of
settings.stream_silence_timeout_seconds, at which point the full buffered
audio is transcribed once more for a final, high-accuracy transcript and
handed to the rest of the assessment pipeline.
"""

import io
import logging
import time
import wave
from dataclasses import dataclass, field
from typing import Callable, Optional

from src.config import settings
from src.voice.transcriber import GroqTranscriber, TranscriptionError

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit PCM
CHANNELS = 1


def pcm16_to_wav_bytes(pcm_bytes: bytes) -> bytes:
    """Wrap raw 16-bit mono PCM in a WAV container Whisper can accept."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


@dataclass
class StreamResult:
    is_final: bool
    text: str
    latency_ms: int


@dataclass
class StreamingSession:
    """
    Buffers PCM16 audio frames from a live caller and produces rolling
    partial transcripts plus a final transcript once silence is detected.
    """

    transcriber: GroqTranscriber
    on_partial: Optional[Callable[[StreamResult], None]] = None
    _buffer: bytearray = field(default_factory=bytearray)
    _last_partial_len: int = 0
    _last_audio_at: float = field(default_factory=time.monotonic)
    _bytes_per_second: int = SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS

    def push_frame(self, pcm_chunk: bytes) -> Optional[StreamResult]:
        """Feed raw PCM16 mono audio. Returns a partial transcript when a
        full rolling window has accumulated since the last one, else None."""
        self._buffer.extend(pcm_chunk)
        self._last_audio_at = time.monotonic()

        window_bytes = int(settings.stream_chunk_seconds * self._bytes_per_second)
        new_bytes = len(self._buffer) - self._last_partial_len
        if new_bytes < window_bytes:
            return None

        self._last_partial_len = len(self._buffer)
        return self._transcribe(bytes(self._buffer), is_final=False)

    def silence_elapsed(self) -> float:
        return time.monotonic() - self._last_audio_at

    def is_utterance_complete(self) -> bool:
        return (
            len(self._buffer) > 0
            and self.silence_elapsed() >= settings.stream_silence_timeout_seconds
        )

    def finalize(self) -> Optional[StreamResult]:
        """Transcribe everything buffered so far as the final utterance and
        reset the session for the next turn."""
        if not self._buffer:
            return None
        result = self._transcribe(bytes(self._buffer), is_final=True)
        self._buffer = bytearray()
        self._last_partial_len = 0
        return result

    def _transcribe(self, pcm_bytes: bytes, is_final: bool) -> StreamResult:
        start = time.monotonic()
        wav_bytes = pcm16_to_wav_bytes(pcm_bytes)
        try:
            text = self.transcriber.transcribe_from_bytes(
                wav_bytes, filename="stream.wav", language="en"
            )
        except TranscriptionError as e:
            logger.warning(f"Streaming transcription window failed: {e}")
            text = ""
        latency_ms = int((time.monotonic() - start) * 1000)
        result = StreamResult(is_final=is_final, text=text, latency_ms=latency_ms)
        if not is_final and self.on_partial:
            self.on_partial(result)
        return result
