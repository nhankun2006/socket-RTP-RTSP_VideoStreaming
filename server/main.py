from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from rtsp_server import RtspServer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RTSP MJPEG server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8089, help="RTSP TCP port")
    parser.add_argument("--video-root", default=".", help="Folder containing MJPEG files")
    parser.add_argument("--fps", type=float, default=25.0, help="Streaming FPS")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = RtspServer(args.host, args.port, Path(args.video_root).resolve(), args.fps)
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
