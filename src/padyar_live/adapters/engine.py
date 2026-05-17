from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


class EngineAdapter(ABC):
    """Abstract interface to PadYar-LipSync engine. No ML code here — external calls only."""

    @abstractmethod
    async def generate_frames(
        self,
        session_id: str,
        audio_chunk: bytes,
        frame_count: int,
    ) -> list[bytes]:
        """Request frame generation from the engine.

        Args:
            session_id: Active session identifier.
            audio_chunk: Raw PCM audio bytes (16kHz mono 16-bit).
            frame_count: Number of frames to generate for this chunk.

        Returns:
            List of JPEG frame bytes.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the engine is reachable."""


class FakeEngineAdapter(EngineAdapter):
    """Returns placeholder frames for testing without a real engine."""

    def __init__(self, frame_width: int = 256, frame_height: int = 256) -> None:
        self._frame_width = frame_width
        self._frame_height = frame_height

    async def generate_frames(
        self,
        session_id: str,
        audio_chunk: bytes,
        frame_count: int,
    ) -> list[bytes]:
        # Simulate realistic engine latency (50-100ms)
        await asyncio.sleep(0.07)
        return [self._placeholder_frame(i) for i in range(frame_count)]

    async def health_check(self) -> bool:
        return True

    def _placeholder_frame(self, index: int) -> bytes:
        # Minimal valid JPEG: 1x1 gray pixel — enough to test the pipeline
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
            b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
            b"\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00"
            b"\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01"
            b"\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07"
            b"\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05"
            b"\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q"
            b"\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19"
            b"\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88"
            b"\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8"
            b"\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8"
            b"\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7"
            b"\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01"
            b"\x01\x00\x00?\x00\x7f\x80\x00\x00\xff\xd9"
        )
