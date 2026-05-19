from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import re
import socket
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from rtp_packet import RtpPacketizer
from video_stream import VideoStream


STATE_INIT = "INIT"
STATE_READY = "READY"
STATE_PLAYING = "PLAYING"


@dataclass
class RtspSession:
    client_addr: Tuple[str, int]
    session_id: str
    video_root: Path
    fps: float
    state: str = STATE_INIT
    cseq: str = "0"
    client_rtp_port: Optional[int] = None
    rtp_socket: Optional[socket.socket] = None
    sender_thread: Optional[threading.Thread] = None
    sending: threading.Event = field(default_factory=threading.Event)
    stream: Optional[VideoStream] = None
    packetizer: RtpPacketizer = field(default_factory=RtpPacketizer)

    def stop_streaming(self) -> None:
        self.sending.clear()
        if self.sender_thread and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=2.0)
        if self.rtp_socket:
            self.rtp_socket.close()
            self.rtp_socket = None


class RtspServer:
    def __init__(self, host: str, port: int, video_root: Path, fps: float = 25.0) -> None:
        self._host = host
        self._port = port
        self._video_root = video_root
        self._fps = fps

    async def start(self) -> None:
        server = await asyncio.start_server(self._handle_client, self._host, self._port)
        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
        print(f"RTSP server listening on {addrs}")
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        if not peer:
            writer.close()
            await writer.wait_closed()
            return

        session = RtspSession(client_addr=(peer[0], peer[1]), session_id=self._new_session_id(), video_root=self._video_root, fps=self._fps)
        print(f"Client connected: {session.client_addr}")

        try:
            while True:
                try:
                    raw = await reader.readuntil(b"\r\n\r\n")
                except asyncio.IncompleteReadError:
                    break

                request = raw.decode("utf-8", errors="replace")
                method, target, headers = self._parse_request(request)
                session.cseq = headers.get("CSeq", "0")

                if method == "SETUP":
                    await self._handle_setup(session, target, headers, writer)
                elif method == "PLAY":
                    await self._handle_play(session, writer)
                elif method == "PAUSE":
                    await self._handle_pause(session, writer)
                elif method == "TEARDOWN":
                    await self._handle_teardown(session, writer)
                    break
                else:
                    await self._send_reply(writer, session.cseq, session.session_id, "501 Not Implemented")
        finally:
            session.stop_streaming()
            writer.close()
            await writer.wait_closed()
            print(f"Client disconnected: {session.client_addr}")

    async def _handle_setup(self, session: RtspSession, target: str, headers: Dict[str, str], writer: asyncio.StreamWriter) -> None:
        match = re.search(r"client_port=(\d+)", headers.get("Transport", ""))
        if not match:
            await self._send_reply(writer, session.cseq, session.session_id, "400 Bad Request")
            return

        session.client_rtp_port = int(match.group(1))
        video_name = Path(target).name
        video_path = (session.video_root / video_name).resolve()

        if not video_path.exists():
            await self._send_reply(writer, session.cseq, session.session_id, "404 Not Found")
            return

        try:
            session.stream = VideoStream(video_path)
        except OSError:
            await self._send_reply(writer, session.cseq, session.session_id, "500 Internal Server Error")
            return

        session.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        session.state = STATE_READY

        await self._send_reply(writer, session.cseq, session.session_id, "200 OK")

    async def _handle_play(self, session: RtspSession, writer: asyncio.StreamWriter) -> None:
        if session.state != STATE_READY or not session.stream or session.client_rtp_port is None:
            await self._send_reply(writer, session.cseq, session.session_id, "455 Method Not Valid in This State")
            return

        session.state = STATE_PLAYING
        session.sending.set()
        if not session.sender_thread or not session.sender_thread.is_alive():
            session.sender_thread = threading.Thread(target=self._stream_loop, args=(session,), daemon=True)
            session.sender_thread.start()

        await self._send_reply(writer, session.cseq, session.session_id, "200 OK")

    async def _handle_pause(self, session: RtspSession, writer: asyncio.StreamWriter) -> None:
        if session.state != STATE_PLAYING:
            await self._send_reply(writer, session.cseq, session.session_id, "455 Method Not Valid in This State")
            return

        session.state = STATE_READY
        session.sending.clear()
        await self._send_reply(writer, session.cseq, session.session_id, "200 OK")

    async def _handle_teardown(self, session: RtspSession, writer: asyncio.StreamWriter) -> None:
        session.state = STATE_INIT
        session.sending.clear()
        await self._send_reply(writer, session.cseq, session.session_id, "200 OK")

    def _stream_loop(self, session: RtspSession) -> None:
        if not session.rtp_socket or session.client_rtp_port is None or not session.stream:
            return

        interval = 1.0 / max(session.fps, 1.0)
        target = (session.client_addr[0], session.client_rtp_port)

        while session.sending.is_set() and session.state == STATE_PLAYING:
            frame = session.stream.get_next_frame()
            if not frame:
                session.sending.clear()
                break

            session.packetizer.begin_frame(frame)
            while session.sending.is_set():
                packet = session.packetizer.get_next_packet()
                if packet is None:
                    break
                try:
                    session.rtp_socket.sendto(packet, target)
                except OSError:
                    session.sending.clear()
                    break

            time.sleep(interval)

    @staticmethod
    async def _send_reply(writer: asyncio.StreamWriter, cseq: str, session_id: str, status: str) -> None:
        response = f"RTSP/1.0 {status}\r\nCSeq: {cseq}\r\nSession: {session_id}\r\n\r\n"
        writer.write(response.encode("ascii"))
        await writer.drain()

    @staticmethod
    def _parse_request(request: str) -> Tuple[str, str, Dict[str, str]]:
        lines = [line for line in request.split("\r\n") if line]
        if not lines:
            return "", "", {}
        request_line = lines[0]
        parts = request_line.split()
        method = parts[0] if len(parts) > 0 else ""
        target = parts[1] if len(parts) > 1 else ""
        headers: Dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()
        return method, target, headers

    @staticmethod
    def _new_session_id() -> str:
        return str(int(time.time() * 1000) % 1000000)
