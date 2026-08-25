"""Live preview of the pose overlay in the browser (auto-refresh).

Run on the Windows host while the Docker launch is up:

    python scripts/watch_preview.py

Opens http://127.0.0.1:8765/ and reloads frames as Docker writes them.
Press Ctrl+C in the terminal to stop.
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>RTMPose live preview</title>
  <style>
    html, body { margin: 0; height: 100%; background: #111; color: #ddd;
                 font-family: system-ui, sans-serif; }
    body { display: flex; flex-direction: column; align-items: center;
           justify-content: center; gap: 12px; }
    img { max-width: 96vw; max-height: 88vh; background: #222; }
    .meta { font-size: 13px; opacity: 0.7; }
  </style>
</head>
<body>
  <img id="frame" alt="Waiting for preview frames"/>
  <div class="meta" id="meta">waiting…</div>
  <script>
    const img = document.getElementById('frame');
    const meta = document.getElementById('meta');
    let ok = 0, fail = 0;
    function tick() {
      const url = '/frame.jpg?t=' + Date.now();
      const probe = new Image();
      probe.onload = () => {
        img.src = url;
        ok += 1;
        meta.textContent = 'live · updates ' + ok + ' · misses ' + fail;
      };
      probe.onerror = () => {
        fail += 1;
        meta.textContent = 'waiting for frames · misses ' + fail;
      };
      probe.src = url;
    }
    setInterval(tick, 250);
    tick();
  </script>
</body>
</html>
"""


def _newest_preview(tmp_dir: Path) -> Path | None:
    frames = sorted(tmp_dir.glob('live_preview.*.jpg'))
    if frames:
        return frames[-1]
    stable = tmp_dir / 'live_preview.jpg'
    return stable if stable.is_file() else None


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    tmp_dir: Path = Path('.')

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split('?', 1)[0]
        if path in ('/', '/index.html'):
            body = PAGE.encode('utf-8')
            self._send(200, 'text/html; charset=utf-8', body)
            return
        if path in ('/frame.jpg', '/live_preview.jpg'):
            file_path = _newest_preview(self.tmp_dir)
            if file_path is None:
                self.send_error(404, 'no preview frame yet')
                return
            try:
                body = file_path.read_bytes()
            except OSError:
                self.send_error(404, 'preview frame unreadable')
                return
            if len(body) < 100:
                self.send_error(404, 'preview frame incomplete')
                return
            self._send(200, 'image/jpeg', body)
            return
        self.send_error(404)

    def _send(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> int:
    parser = argparse.ArgumentParser(description='Browser live view of the pose overlay.')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-open', action='store_true', help='Do not open a browser tab')
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    tmp_dir = repo / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    class BoundHandler(PreviewHandler):
        pass

    BoundHandler.tmp_dir = tmp_dir
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('127.0.0.1', args.port), BoundHandler) as httpd:
        url = f'http://127.0.0.1:{args.port}/'
        print(f'Live preview at {url}')
        print(f'Serving newest live_preview.*.jpg from {tmp_dir} — Ctrl+C to stop.')
        if not args.no_open:
            threading.Timer(0.4, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nstopped')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
