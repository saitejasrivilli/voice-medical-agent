"""
Text-to-speech synthesis for agent responses.
Default backend is gTTS (free, no API key). If ELEVENLABS_API_KEY is set,
uses ElevenLabs for higher-quality, lower-latency speech.
"""

import io
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class SynthesisError(Exception):
    """Raised when speech synthesis fails."""
    pass


class GTTSSynthesizer:
    """Free TTS backend using gTTS (Google Translate TTS)."""

    def synthesize(self, text: str, lang: str = "en") -> bytes:
        if not text or not text.strip():
            raise SynthesisError("Cannot synthesize empty text")
        try:
            from gtts import gTTS
        except ImportError:
            raise ImportError("gTTS not installed. Install with: pip install gTTS")

        try:
            buf = io.BytesIO()
            gTTS(text=text, lang=lang).write_to_fp(buf)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            raise SynthesisError(f"gTTS synthesis failed: {str(e)}")


class ElevenLabsSynthesizer:
    """Low-latency TTS backend using ElevenLabs (requires API key)."""

    def __init__(self, api_key: str, voice_id: Optional[str] = None):
        self.api_key = api_key
        self.voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"  # default "Rachel" voice

    def synthesize(self, text: str, lang: str = "en") -> bytes:
        if not text or not text.strip():
            raise SynthesisError("Cannot synthesize empty text")
        try:
            import requests
        except ImportError:
            raise ImportError("requests not installed")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            raise SynthesisError(f"ElevenLabs synthesis failed: {str(e)}")


def get_synthesizer():
    """Return ElevenLabs synthesizer if configured, otherwise fall back to gTTS."""
    api_key = getattr(settings, "elevenlabs_api_key", "")
    if api_key:
        return ElevenLabsSynthesizer(api_key=api_key)
    return GTTSSynthesizer()
