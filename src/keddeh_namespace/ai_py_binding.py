"""Bounded host-side AI.PY operations via the existing authenticated WEB4 controller.

This is not the browser's Python/WASM interpreter and does not create a host.
A successful local binding means this authenticated gateway can reach its own
pinned worker processes. It does not attest that the external Site is routed here.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import threading

SCHEMA = "braink.ai-py.server-binding.v1"
REQUEST_SCHEMA = "braink.ai-py.execution-request.v1"
RECEIPT_SCHEMA = "braink.ai-py.execution-receipt.v1"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,79}$")
OPERATIONS = {
    "mesh_discover": ("estate", "mesh_discover"),
    "mesh_status": ("estate", "mesh_status"),
    "workbook_diagnostic": ("workbook", None),
    "web4_status": ("status", None),
}
MAX_RESULT_BYTES = 256 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _write_durable(path, value):
    """Atomic same-directory replace with file AND directory sync."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + "." + secrets.token_hex(8))
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(canonical(value) + b"\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        dirfd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _load_checked(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(MAX_RESULT_BYTES + 4096)
    if len(raw) > MAX_RESULT_BYTES + 4095:
        raise ValueError("AI_PY_RECEIPT_SIZE_EXCEEDED")
    record = json.loads(raw)
    expected = record.pop("receiptDigest", None)
    if not isinstance(expected, str) or digest(record) != expected:
        raise ValueError("AI_PY_RECEIPT_INTEGRITY_FAILURE")
    record["receiptDigest"] = expected
    return record


class HostBinding:
    def __init__(self, controller):
        self.controller = controller
        self.lock = threading.RLock()
        self.receipts = Path(controller.state) / "ai-py" / "receipts"

    def status(self):
        info = self.controller.status()
        services = info.get("services") or {}
        estate = services.get("estate") or {}
        configured = len(self.controller.ports.get("mesh", []))
        ready = bool(estate.get("alive") is True and configured > 0
                     and info.get("healthy_nodes") == configured
                     and info.get("schema") == "keddeh.web4.readback.v1")
        return {
            "schema": SCHEMA,
            "connected": ready,
            "state": "AUTHENTICATED_LOCAL_EXECUTION_READY" if ready else "NO_PYTHON_HOST_BINDING",
            "scope": "CURRENT_AUTHENTICATED_WEB4_GATEWAY_ONLY",
            "siteDeploymentVerified": False,
            "arbitraryPythonExecution": False,
            "ownerRuntimeSourceDigest": self.controller.source_digest,
            "observedAt": now(),
            "observedWorkstations": info.get("healthy_nodes", 0),
            "declaredWorkstations": configured,
            "operations": sorted(OPERATIONS),
        }

    def _path(self, request_id):
        if not isinstance(request_id, str) or not ID_PATTERN.fullmatch(request_id):
            raise ValueError("INVALID_AI_PY_REQUEST_ID")
        return self.receipts / (request_id + ".json")

    def receipt(self, request_id):
        path = self._path(request_id)
        with self.lock:
            try:
                record = _load_checked(path)
            except FileNotFoundError:
                return None
            if record.get("requestId") != request_id or record.get("schema") != RECEIPT_SCHEMA:
                raise ValueError("AI_PY_RECEIPT_IDENTITY_MISMATCH")
            return record

    def _persist(self, record):
        obj = {**record, "receiptDigest": digest(record)}
        _write_durable(self._path(record["requestId"]), obj)
        return self.receipt(record["requestId"])

    def execute(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"schema", "requestId", "operation", "arguments"}:
            raise ValueError("INVALID_AI_PY_EXECUTION_ENVELOPE")
        if payload["schema"] != REQUEST_SCHEMA or payload["operation"] not in OPERATIONS:
            raise ValueError("UNSUPPORTED_AI_PY_OPERATION")
        if payload["arguments"] != {}:
            raise ValueError("AI_PY_OPERATION_ARGUMENTS_NOT_ADMITTED")
        request_id = payload["requestId"]
        self._path(request_id)
        fingerprint = digest(payload)
        with self.lock:
            prior = self.receipt(request_id)
            if prior is not None:
                if prior["inputDigest"] != fingerprint:
                    raise ValueError("AI_PY_REQUEST_ID_COLLISION")
                return {**prior, "replay": True}
            if not self.status()["connected"]:
                raise RuntimeError("NO_PYTHON_HOST_BINDING")
            # Commit pending BEFORE dispatch. On crash, retry cannot re-execute blindly.
            base = {
                "schema": RECEIPT_SCHEMA,
                "requestId": request_id,
                "inputDigest": fingerprint,
                "operation": payload["operation"],
                "sourceDigest": self.controller.source_digest,
                "createdAt": now(),
                "state": "PENDING",
                "effect": "NOT_YET_RECONCILED",
            }
            self._persist(base)
            try:
                kind, tool = OPERATIONS[payload["operation"]]
                if kind == "estate":
                    result = self.controller.control({"action": "estate", "tool": tool, "arguments": {}})
                elif kind == "workbook":
                    result = self.controller.control({"action": "workbook"})
                else:
                    result = self.controller.status()
                raw = canonical(result)
                if len(raw) > MAX_RESULT_BYTES:
                    raise RuntimeError("AI_PY_RESULT_TOO_LARGE_FOR_RECEIPT")
            except Exception as exc:
                # The operation MAY have run. Never present a definite failure or retry it.
                return self._persist({**base, "state": "OUTCOME_UNCERTAIN",
                                      "errorClass": type(exc).__name__, "observedAt": now()})
            return self._persist({**base, "state": "RECORDED", "resultDigest": hashlib.sha256(raw).hexdigest(),
                                  "result": result, "effect": "READ_ONLY_EXECUTED_AND_RETAINED",
                                  "observedAt": now()})
