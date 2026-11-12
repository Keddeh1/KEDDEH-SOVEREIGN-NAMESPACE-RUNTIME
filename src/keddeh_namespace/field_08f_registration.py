"""Register the pinned 08F worker without pairing, spawning or adopting a PID.

The owner supplies an existing enrollment path in launch.json. Secret values
remain host-owned; optional forwarding accepts only explicitly named bindings.
This module does not turn the worker's HMAC receipts into R8/R10 evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

HOST_ID = "web4-2d5eefa3698ab755ed10237462171cf472675b83e0aa01994a817f3164ed1f8d"
SERVICE_NAME = "keddeh-field-08f.service"
ENTRY_RELATIVE = "packages/08f-v2.1/08F_kex_self_host_node_v2_1.py"
ENTRY_SHA256 = "7f6435c183f444fbf1913028cec4bc94795528b7c334b02c55edf79d359a4eb9"
ARCHIVE_BYTES = 51837
ARCHIVE_SHA256 = "6f1b502500ae971bc067f416aaa7e9f353bd08424f5c2d262c86899a013d4f21"
ALLOWED_HOST_ENV_NAMES = frozenset({
    "BRAINK_MCP_HMAC_KEY_HEX", "KEX_RECEIPT_HMAC_KEY_HEX", "BRAINK_MCP_DATA_DIR",
})


def _same_file(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True
    return left.exists() and right.exists() and os.path.samefile(left, right)


def _state_path(controller, value: str) -> Path:
    if type(value) is not str or not value or not Path(value).is_absolute():
        raise ValueError("08F requires an explicit existing absolute state_file")
    unresolved = Path(value)
    if unresolved.is_symlink():
        raise ValueError("08F state_file symlink rejected")
    state = unresolved.resolve(strict=True)
    if not state.is_file():
        raise ValueError("08F existing enrollment state file required")
    root = Path(controller.root).resolve(strict=True)
    if state.is_relative_to((root / "packages").resolve(strict=True)):
        raise ValueError("08F mutable enrollment cannot live in admitted packages")
    if _same_file(state, root / "state/agent.json"):
        raise ValueError("08F cannot share the standard agent enrollment")
    try:
        enrollment = json.loads(state.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        raise ValueError("08F enrollment state is invalid") from None
    if type(enrollment) is not dict or any(
        type(enrollment.get(key)) is not str or not enrollment[key]
        for key in ("broker", "nodeId", "credential", "name", "workspace")
    ):
        raise ValueError("08F existing enrollment state is incomplete")
    if type(enrollment.get("nextSequence")) is not int or enrollment["nextSequence"] < 1:
        raise ValueError("08F enrollment sequence must be a positive integer")
    broker = urlsplit(enrollment["broker"])
    if (broker.scheme != "https" or not broker.hostname or broker.path not in ("", "/") or broker.username
            or broker.password or broker.query or broker.fragment):
        raise ValueError("08F retained broker must be an HTTPS origin")
    workspace = Path(enrollment["workspace"])
    if not workspace.is_absolute() or not workspace.is_dir():
        raise ValueError("08F retained workspace must be an existing absolute directory")
    return state


def host_environment(names) -> dict[str, str] | None:
    if (type(names) is not list or any(type(name) is not str for name in names)
            or len(names) != len(set(names)) or not set(names) <= ALLOWED_HOST_ENV_NAMES):
        raise ValueError("08F host environment names are invalid")
    values = {}
    for name in names:
        value = os.environ.get(name, "")
        if not value:
            raise ValueError("08F requested host binding is missing: " + name)
        if name.endswith("_HMAC_KEY_HEX"):
            if not re.fullmatch(r"(?:[0-9a-fA-F]{2}){32,}", value):
                raise ValueError("08F requested HMAC binding is invalid: " + name)
        elif not Path(value).is_absolute():
            raise ValueError("08F host data directory must be absolute")
        values[name] = value
    return values or None


def registration_options(config):
    """Validate the optional config shape without reading enrollment or secrets."""
    if "field_08f" not in config:
        return None
    options = config["field_08f"]
    if (type(options) is not dict or "state_file" not in options
            or set(options) - {"state_file", "pass_host_env_names"}):
        raise ValueError("08F configuration requires state_file and optional pass_host_env_names")
    return options


def register_configured_08f(controller):
    """Apply the optional registration before host activation and any spawning.

    Missing field_08f leaves the existing service set unchanged. Present but
    incomplete configuration fails closed. This is registration only: the owned
    host actuator still requires fresh descriptors for a later explicit start.
    """
    options = registration_options(controller.config)
    if options is None:
        return None
    if controller.host_id != HOST_ID:
        raise ValueError("08F target host identity mismatch")
    root = Path(controller.root).resolve(strict=True)
    original = root / ENTRY_RELATIVE
    entry = original.resolve(strict=True)
    if original.is_symlink() or not entry.is_relative_to((root / "packages").resolve(strict=True)):
        raise ValueError("08F entry must remain inside admitted packages")
    if controller.config["files"].get(ENTRY_RELATIVE) != ENTRY_SHA256:
        raise ValueError("08F entry is missing from the preserved launch manifest")
    if hashlib.sha256(entry.read_bytes()).hexdigest() != ENTRY_SHA256:
        raise ValueError("08F candidate source digest mismatch")
    state = _state_path(controller, options["state_file"])
    extra = host_environment(options.get("pass_host_env_names", []))
    argv = [sys.executable, str(entry), "--state-file", str(state), "--poll-interval", "5"]
    spec = (argv, str(entry.parent), extra, False)
    with controller.lock:
        for name, (other_argv, other_cwd, _, _) in controller.specs.items():
            if name == SERVICE_NAME or "--state-file" not in other_argv:
                continue
            index = other_argv.index("--state-file") + 1
            if index < len(other_argv):
                other_path = Path(other_argv[index])
                if not other_path.is_absolute():
                    other_path = Path(other_cwd) / other_path
                if _same_file(state, other_path):
                    raise ValueError("08F enrollment already belongs to another service")
        if SERVICE_NAME in controller.specs and controller.specs[SERVICE_NAME] != spec:
            raise ValueError("08F owned service specification collision")
        if SERVICE_NAME in controller.processes and SERVICE_NAME not in controller.specs:
            raise ValueError("08F process has no owned specification")
        controller.specs[SERVICE_NAME] = spec
    return {
        "name": SERVICE_NAME, "entry_sha256": ENTRY_SHA256, "registered": True,
        "process_started": False, "pairing_performed": False,
        "actuator_policy_changed": False, "host_env_names": sorted(extra or {}),
    }
