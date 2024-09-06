"""Read-only HTTP server exposing cookbook JSON.

Author: Marwan Helmy

Uses stdlib only — handy for phone dashboard on LAN.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

from .storage import JsonStorage


class CookbookHTTPHandler(BaseHTTPRequestHandler):
    storage: JsonStorage  # set on handler class before serve

    def log_message(self, format, *args):
        pass  # quiet by default — TODO: optional verbose mode

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status=status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/":
            self._send_json({
                "service": "boardbox",
                "endpoints": [
                    "/cookbook",
                    "/sessionbook",
                    "/games",
                    "/games/{id}",
                    "/campaigns",
                    "/bin",
                    "/favorites",
                    "/health",
                ],
            })
            return

        if path == "/health":
            self._send_json({"ok": True})
            return

        if path in ("/cookbook", "/sessionbook"):
            self._send_json(self.storage.snapshot())
            return

        if path == "/games":
            active = qs.get("active", ["true"])[0].lower() != "false"
            publisher_name = qs.get("publisher_name", [None])[0]
            format = qs.get("format", [None])[0]
            games = self.storage.list_games(active_only=active)
            if publisher_name:
                games = [r for r in games if r.publisher_name.lower() == publisher_name.lower()]
            if format:
                games = [r for r in games if r.format.lower() == format.lower()]
            self._send_json({
                "games": [r.to_dict() for r in games],
                "count": len(games),
            })
            return

        if path.startswith("/games/"):
            game_id = path.split("/games/", 1)[1]
            if not game_id or "/" in game_id:
                self._send_error_json("invalid game id", 400)
                return
            try:
                game = self.storage.get_game(game_id)
            except Exception:
                self._send_error_json("game not found", 404)
                return
            self._send_json(game.to_dict())
            return

        if path == "/campaigns":
            self._send_json({
                "campaigns": self.storage.list_campaigns(),
                "count": len(self.storage.list_campaigns()),
            })
            return

        if path == "/bin" or path == "/bins":
            self._send_json({
                "bin": self.storage.list_bin(),
                "count": len(self.storage.list_bin()),
            })
            return

        if path == "/favorites":
            fav_ids = self.storage.list_favorites()
            games = []
            for fid in fav_ids:
                try:
                    games.append(self.storage.get_game(fid).to_dict())
                except Exception:
                    pass
            self._send_json({"favorites": games, "count": len(games)})
            return

        if path == "/tags":
            self._send_json({"tags": self.storage.list_tags()})
            return

        self._send_error_json("not found", 404)

    def do_POST(self) -> None:
        self._send_error_json("read-only server", 405)

    def do_PUT(self) -> None:
        self.do_POST()

    def do_DELETE(self) -> None:
        self.do_POST()


class CampaignServer:
    def __init__(self, storage: JsonStorage, host: str = "127.0.0.1", port: int = 8766):
        self.storage = storage
        self.host = host
        self.port = port
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def serve_forever(self) -> None:
        handler = type("BoundHandler", (CookbookHTTPHandler,), {})
        handler.storage = self.storage
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._httpd.serve_forever()

    def start_background(self) -> ThreadingHTTPServer:
        handler = type("BoundHandler", (CookbookHTTPHandler,), {})
        handler.storage = self.storage
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self._httpd

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    @property
    def address(self) -> tuple[str, int]:
        if self._httpd:
            return self._httpd.server_address  # type: ignore
        return (self.host, self.port)


def run_server(cookbook_path: str, host: str = "127.0.0.1", port: int = 8766) -> None:
    storage = JsonStorage(cookbook_path)
    CampaignServer(storage, host=host, port=port).serve_forever()
