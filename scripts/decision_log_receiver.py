#!/usr/bin/env python3
"""
OPA Decision Log Receiver
"""

import gzip
import io
import json
import os
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3
from botocore.client import Config

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD")
MINIO_AUDIT_BUCKET = os.getenv("MINIO_AUDIT_BUCKET", "audit-logs")
PORT = int(os.getenv("PORT", "8090"))

s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ROOT_USER,
    aws_secret_access_key=MINIO_ROOT_PASSWORD,
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    region_name="us-east-1",
)


class DecisionLogHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[decision-log-receiver] {fmt % args}")

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/logs":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)

        if self.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)

        try:
            events = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"invalid decision log batch: {exc}".encode())
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        key = f"decision-logs/{timestamp}_{uuid.uuid4().hex[:8]}.json"
        body = json.dumps(events, indent=2).encode()

        s3.put_object(
            Bucket=MINIO_AUDIT_BUCKET,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

        print(f"[decision-log-receiver] stored {len(events)} decision(s) -> s3://{MINIO_AUDIT_BUCKET}/{key}")

        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DecisionLogHandler)
    print(f"[decision-log-receiver] listening on :{PORT}, writing to s3://{MINIO_AUDIT_BUCKET}/decision-logs/")
    server.serve_forever()
