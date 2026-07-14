"""
Audio transcription service using Groq Whisper API.
Handles transcription with error handling, fallback strategies, and validation.
"""

import logging
from typing import Optional
import os
import hashlib
from src.config import settings

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Base exception for transcription failures."""
    pass


class GroqTranscriber:
    """Groq Whisper transcription service."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize Groq transcriber.
        
        Args:
            api_key: Groq API key (defaults to env variable)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise ValueError("Groq API key not provided. Set GROQ_API_KEY env variable.")
        
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError("Groq SDK not installed. Install with: pip install groq")
        
        self.timeout = timeout
        self.model = settings.groq_model

    def validate_audio_file(self, file_path: str) -> tuple[bool, str]:
        """
        Validate audio file exists and is correct format.
        
        Returns:
            (is_valid, error_message)
        """
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > settings.max_audio_size_mb:
            return False, f"File too large: {file_size_mb:.1f}MB (max {settings.max_audio_size_mb}MB)"
        
        # Check file extension
        valid_extensions = ['.wav', '.mp3', '.webm', '.m4a', '.flac', '.ogg']
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in valid_extensions:
            return False, f"Invalid file format: {ext}. Supported: {valid_extensions}"
        
        return True, ""

    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of audio file for deduplication."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def transcribe(
        self,
        file_path: str,
        language: str = "en",
        fallback_to_text: bool = True,
    ) -> tuple[str, Optional[str], int]:
        """
        Transcribe audio file.
        
        Args:
            file_path: Path to audio file
            language: Language code (default: en)
            fallback_to_text: If True, raise error to prompt manual input on failure
            
        Returns:
            (transcribed_text, file_hash, duration_seconds)
            
        Raises:
            TranscriptionError: If transcription fails
        """
        # Validate file
        is_valid, error_msg = self.validate_audio_file(file_path)
        if not is_valid:
            logger.error(f"Audio validation failed: {error_msg}")
            raise TranscriptionError(f"Audio validation failed: {error_msg}")

        # Calculate file hash for deduplication
        try:
            file_hash = self.calculate_file_hash(file_path)
        except Exception as e:
            logger.error(f"Failed to calculate file hash: {str(e)}")
            raise TranscriptionError(f"Failed to process audio file: {str(e)}")

        # Perform transcription
        try:
            logger.info(f"Starting transcription for {file_path}")
            
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=(os.path.basename(file_path), audio_file),
                    language=language,
                )
            
            text = transcript.text
            
            if not text or text.strip() == "":
                error = "Transcription returned empty result"
                logger.warning(error)
                raise TranscriptionError(error)
            
            logger.info(f"Transcription successful. Length: {len(text)} chars")
            return text, file_hash, 0  # Duration would come from metadata if available
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Groq transcription failed: {error_msg}")
            
            if fallback_to_text:
                raise TranscriptionError(
                    f"Audio transcription failed: {error_msg}. "
                    "Please provide symptoms as text instead."
                )
            raise TranscriptionError(f"Transcription failed: {error_msg}")

    def transcribe_from_bytes(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: str = "en",
    ) -> str:
        """
        Transcribe audio from bytes (for uploaded files).
        
        Args:
            audio_bytes: Raw audio data
            filename: Filename for the audio
            language: Language code
            
        Returns:
            Transcribed text
        """
        try:
            if len(audio_bytes) > settings.max_audio_size_mb * 1024 * 1024:
                raise TranscriptionError(
                    f"Audio too large: {len(audio_bytes) / (1024*1024):.1f}MB "
                    f"(max {settings.max_audio_size_mb}MB)"
                )
            
            logger.info(f"Transcribing {len(audio_bytes)} bytes")
            
            transcript = self.client.audio.transcriptions.create(
                model=self.model,
                file=(filename, audio_bytes),
                language=language,
            )
            
            text = transcript.text
            if not text or text.strip() == "":
                raise TranscriptionError("Transcription returned empty result")
            
            logger.info(f"Transcription successful from bytes")
            return text
            
        except Exception as e:
            logger.error(f"Transcription from bytes failed: {str(e)}")
            raise TranscriptionError(f"Transcription failed: {str(e)}")


class MockTranscriber:
    """Mock transcriber for testing without API calls."""

    def __init__(self):
        self.call_count = 0

    def transcribe(self, file_path: str, language: str = "en", fallback_to_text: bool = True) -> tuple[str, str, int]:
        """Return mock transcription."""
        self.call_count += 1
        
        # Map filenames to mock responses
        mock_responses = {
            "chest_pain.wav": "I have severe chest pain and shortness of breath. It started suddenly about 2 hours ago.",
            "knee_injury.wav": "My knee is swollen and painful after I fell yesterday. I can barely move it.",
            "rash.wav": "There's a weird red rash on my arm that appeared 3 weeks ago. It's itchy and spreading.",
        }
        
        filename = file_path.split("/")[-1]
        text = mock_responses.get(filename, "Patient reports general symptoms requiring medical assessment.")
        
        return text, "mock_hash_123", 30

    def transcribe_from_bytes(self, audio_bytes: bytes, filename: str = "audio.wav", language: str = "en") -> str:
        """Return mock transcription from bytes."""
        return "Mock transcribed audio: patient reports symptoms requiring medical evaluation."
