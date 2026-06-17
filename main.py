#!/usr/bin/env python3
"""Daily Predictor - HTTP server serving frontend and prediction JSON files."""
import http.server
import socketserver
from pathlib import Path

PORT = 8080
OUTPUT_DIR = Path(__file__).parent / "output"
FRONTEND_DIR = Path(__file__).parent / "frontend"

class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith('/output/'):
            return str(OUTPUT_DIR / path[len('/output/'):])
        if path == '/':
            return str(FRONTEND_DIR / 'index.html')
        return str(FRONTEND_DIR / path.lstrip('/'))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        httpd.serve_forever()
