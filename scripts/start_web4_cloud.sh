#!/usr/bin/env bash
set -euo pipefail
cd /workspace/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME
runtime_root=${KEDDEH_WEB4_ROOT:-/workspace/braink-setup/web4-runtime}
library_manifest=${KEDDEH_LIBRARY_MANIFEST:-/workspace/library-files/KEDDEH/2026-10-07/manifest.json}
if [ ! -f "$runtime_root/launch.json" ]; then
  .venv/bin/python -m keddeh_namespace.web4_runtime prepare --root "$runtime_root" --library "$library_manifest"
fi
if .venv/bin/python -m keddeh_namespace.web4_runtime status --root "$runtime_root" >/dev/null 2>&1; then
  .venv/bin/python -m keddeh_namespace.web4_runtime status --root "$runtime_root"
else
  .venv/bin/python -m keddeh_namespace.web4_runtime start --root "$runtime_root"
fi
.venv/bin/python scripts/bootstrap_owner_environment.py --root "$runtime_root"
