#!/usr/bin/env python3
"""
Daily Predictor - Sports Prediction Web App
Entry point for Replit. Serves the frontend and output files.
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 8080
OUTPUT_DIR = Path(__file__).parent / "output"
FRONTEND_DIR = Path(__file__).parent / "frontend"

class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve output files from /output/ path
        if path.startswith('/output/'):
            relative = path[len('/output/'):]
            return str(OUTPUT_DIR / relative)
        # Serve frontend files
        if path == '/':
            return str(FRONTEND_DIR / 'index.html')
        return str(FRONTEND_DIR / path.lstrip('/'))

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving Daily Predictor at http://localhost:{PORT}")
        httpd.serve_forever()
