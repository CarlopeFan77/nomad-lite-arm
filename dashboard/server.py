#!/usr/bin/env python3

import json
import subprocess
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "dashboard" / "static"
CATALOG_FILE = PROJECT_DIR / "config" / "library-catalog.txt"
ZIM_DIR = PROJECT_DIR / "data" / "zim"
NOMAD_COMMAND = PROJECT_DIR / "nomad"

HOST = "127.0.0.1"
PORT = 8081


def run_nomad(*args):
    try:
        result = subprocess.run(
            [str(NOMAD_COMMAND), *args],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=15,
        )

        output = result.stdout.strip()

        if result.stderr.strip():
            output += "\n" + result.stderr.strip()

        return {
            "success": result.returncode == 0,
            "output": output.strip(),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "Command timed out.",
        }


def read_library():
    collections = []

    if not CATALOG_FILE.exists():
        return collections

    for line in CATALOG_FILE.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        parts = line.split("|", 4)

        if len(parts) != 5:
            continue

        collection_id, name, size, filename, url = parts

        collections.append(
            {
                "id": collection_id,
                "name": name,
                "size": size,
                "filename": filename,
                "installed": (ZIM_DIR / filename).exists(),
            }
        )

    return collections


class NomadHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=str(STATIC_DIR),
            **kwargs,
        )

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)

    def do_GET(self):

        if self.path == "/api/status":
            result = run_nomad("status")

            result["running"] = (
                "Kiwix is running" in result["output"]
            )

            self.send_json(result)
            return

        if self.path == "/api/system":
            self.send_json(run_nomad("system"))
            return

        if self.path == "/api/library":
            self.send_json(
                {
                    "collections": read_library()
                }
            )
            return

        super().do_GET()

    def do_POST(self):

        if self.path == "/api/start":
            self.send_json(run_nomad("start"))
            return

        if self.path == "/api/stop":
            self.send_json(run_nomad("stop"))
            return

        self.send_json(
            {"success": False, "output": "Unknown action."},
            status=404,
        )


def main():
    server = ThreadingHTTPServer(
        (HOST, PORT),
        NomadHandler,
    )

    print()
    print("NOMAD Lite ARM Dashboard")
    print("========================")
    print(f"Running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
