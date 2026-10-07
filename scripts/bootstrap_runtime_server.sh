#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 2 ]; then
  echo 'Usage: bootstrap_runtime_server.sh CONFIG ACCEPTANCE_LEDGER' >&2
  exit 2
fi
python -m keddeh_namespace.bootstrap "$1" "$2"
