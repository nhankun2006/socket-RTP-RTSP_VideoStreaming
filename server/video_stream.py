from __future__ import annotations

from pathlib import Path
from typing import Optional, BinaryIO


JPEG_START = b"\xFF\xD8"
JPEG_END = b"\xFF\xD9"


class VideoStream:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: Optional[BinaryIO] = None
        self._open_file(path)

    def _open_file(self, path: Path) -> None:
        if self._file:
            self._file.close()
        self._file = path.open("rb")

    def get_next_frame(self) -> Optional[bytes]:
        if not self._file:
            return None

        prev = b""
        while True:
            cur = self._file.read(1)
            if not cur:
                return None
            if prev + cur == JPEG_START:
                frame = bytearray(JPEG_START)
                prev_byte = JPEG_START[1:2]
                while True:
                    byte = self._file.read(1)
                    if not byte:
                        return None
                    frame += byte
                    if prev_byte + byte == JPEG_END:
                        return bytes(frame)
                    prev_byte = byte
            prev = cur
