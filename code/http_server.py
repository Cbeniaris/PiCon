import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

ROM_DIR  = os.path.expanduser("~/web/roms")
SAVE_DIR = os.path.expanduser("~/web/saves")
WEB_DIR  = os.path.expanduser("~/web")

ROM_EXTS = (".gba", ".gb", ".gbc", ".nes", ".sfc", ".smc", ".snes",
            ".md",  ".bin", ".sms", ".gg", ".pce", ".lnx", ".ngp", ".ngc", ".ws", ".wsc")

os.makedirs(SAVE_DIR, exist_ok=True)


def scan_roms():
    """Return a list of {console, name} dicts, one per ROM file found in subfolders."""
    entries = []
    if not os.path.isdir(ROM_DIR):
        return entries
    for console in sorted(os.listdir(ROM_DIR)):
        console_path = os.path.join(ROM_DIR, console)
        if not os.path.isdir(console_path):
            continue
        for fname in sorted(os.listdir(console_path)):
            if fname.lower().endswith(ROM_EXTS):
                entries.append({"console": console, "name": fname})
    return entries


class Handler(SimpleHTTPRequestHandler):

    def do_GET(self):
        path = unquote(self.path)

        if path == "/roms":
            # Return [{console, name}, ...]
            self._json(scan_roms())

        elif path.startswith("/roms/"):
            # Serve individual ROM file: /roms/<console>/<filename>
            parts = path[6:].split("/", 1)   # strip leading "/roms/"
            if len(parts) == 2:
                console, filename = parts
                filepath = os.path.join(ROM_DIR, console, filename)
                if os.path.isfile(filepath):
                    self._send_file(filepath)
                else:
                    self._404()
            else:
                self._404()

        elif path == "/saves":
            saves = sorted(os.listdir(SAVE_DIR))
            self._json(saves)

        elif path.startswith("/saves/"):
            filename = path[7:]
            filepath = os.path.join(SAVE_DIR, filename)
            if os.path.exists(filepath):
                self._send_file(filepath)
            else:
                self._404()

        else:
            self.directory = WEB_DIR
            super().do_GET()

    def do_POST(self):
        path = unquote(self.path)
        if path.startswith("/saves/"):
            filename = path[7:]
            filepath = os.path.join(SAVE_DIR, filename)
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            with open(filepath, "wb") as f:
                f.write(data)
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self._404()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- helpers ----

    def _send_file(self, filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _404(self):
        self.send_response(404)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print("HTTP server on 0.0.0.0:8080")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
