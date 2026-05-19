from __future__ import annotations

from dataclasses import dataclass
import os
import random
from typing import Optional


MAX_RTP_PAYLOAD = 1200
PAYLOAD_TYPE_JPEG = 26
TIMESTAMP_INCREMENT = 3600


@dataclass
class RtpPacketizer:
    ssrc: int = random.randint(1, 0xFFFFFFFF)
    seq_num: int = 0
    timestamp: int = 0
    _payload: bytes = b""
    _offset: int = 0

    def begin_frame(self, frame_data: bytes) -> None:
        self._payload = frame_data
        self._offset = 0
        self.timestamp = (self.timestamp + TIMESTAMP_INCREMENT) & 0xFFFFFFFF

    def get_next_packet(self) -> Optional[bytes]:
        if self._offset >= len(self._payload):
            return None

        remaining = len(self._payload) - self._offset
        is_last = remaining <= MAX_RTP_PAYLOAD
        payload_len = remaining if is_last else MAX_RTP_PAYLOAD

        header = bytearray(12)
        header[0] = 2 << 6
        header[1] = PAYLOAD_TYPE_JPEG | (0x80 if is_last else 0x00)

        seq = self.seq_num & 0xFFFF
        self.seq_num = (self.seq_num + 1) & 0xFFFF

        header[2] = (seq >> 8) & 0xFF
        header[3] = seq & 0xFF

        ts = self.timestamp
        header[4] = (ts >> 24) & 0xFF
        header[5] = (ts >> 16) & 0xFF
        header[6] = (ts >> 8) & 0xFF
        header[7] = ts & 0xFF

        ssrc = self.ssrc
        header[8] = (ssrc >> 24) & 0xFF
        header[9] = (ssrc >> 16) & 0xFF
        header[10] = (ssrc >> 8) & 0xFF
        header[11] = ssrc & 0xFF

        chunk = self._payload[self._offset:self._offset + payload_len]
        self._offset += payload_len

        return bytes(header) + chunk
