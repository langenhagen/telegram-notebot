"""Local speech-to-text via faster-whisper (lazy model loading)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from faster_whisper import WhisperModel

if TYPE_CHECKING:
    from pathlib import Path

    from notebot.config import WhisperConfig

logger = logging.getLogger(__name__)


class Transcriber:
    """Lazy faster-whisper wrapper; the heavy model loads on first use."""

    def __init__(self, config: WhisperConfig) -> None:
        """Store the settings; the model itself loads lazily."""
        self._config = config
        self._model: WhisperModel | None = None

    def _ensure_model(self) -> WhisperModel:
        """Load the model on first use and return it."""
        if self._model is None:
            logger.info(
                "Loading whisper model '%s' (device=%s, compute_type=%s)",
                self._config.model,
                self._config.device,
                self._config.compute_type,
            )
            self._model = WhisperModel(
                self._config.model,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe an audio file; language is auto-detected (e.g. DE/EN)."""
        segments, info = self._ensure_model().transcribe(
            str(audio_path),
            language=None,
            vad_filter=True,
        )
        logger.info(
            "Detected language %s (probability %.2f)",
            info.language,
            info.language_probability,
        )
        return " ".join(
            segment.text.strip() for segment in segments if segment.text.strip()
        )
