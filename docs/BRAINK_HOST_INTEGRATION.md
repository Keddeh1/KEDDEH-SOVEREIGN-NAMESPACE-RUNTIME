# Existing BRAINK call route and host actuation

## What was missing

The actual owner runtime launches the hash-pinned estate `server/braink_mcp.py` as the `estate` stdio process. Its `handle()` routes JSON-RPC `tools/call` through `TOOLS` and returns `structuredContent`. Existing host-agent tools inspect capabilities or run substrate preparation; none called the WEB4 service lifecycle. The separate `BRAINK-BETA-TEST/braink/domain/dispatcher.py` currently contains a placeholder `{"status":"generated"}` completion and no executable registration. That placeholder is not used or claimed as execution by this integration.

## Implemented route

1. Existing authenticated owner HTTP ingress: `POST /api/web4/control` on the gateway port from `<runtime_root>/launch.json` (default loopback `127.0.0.1:18087`). Request is `{"action":"estate","tool":"host_actuator","arguments":{...}}`.
2. Existing `LaunchController.estate_rpc('tools/call',...)` sends the operation to the actual BRAINK stdio dispatcher. `bind_braink_host_source()` adds one tool definition and one `TOOLS` entry to its derived source; admitted originals and all ten source pins are retained.
3. Derived `server/host_actuator_adapter.py`, sourced from `_braink_host_bridge.py`, accepts only status/start/stop/restart and descriptor-bound arguments. It calls the same gateway's `action: host` using the existing owner token file. The gateway port and token-file path are supplied only to the estate child process; no new credential is created or sent in an operation payload.
4. The existing HTTP authentication, owner-kernel route, projection agreement (when supplied), pipeline generation and service identity/generation/PID checks apply at the actual mutation. The outer stdio dispatch does not hold the pipeline lock while waiting for its HTTP callback, avoiding a callback deadlock. It does not refresh the caller's stale service/pipeline binding.
5. The native actuator starts/stops/restarts the existing owned specification and durably records the result in `state/host-actuator.json`. That actual result returns through BRAINK `structuredContent`, through the original HTTP request, to the caller. Browser service buttons and terminal start/stop/restart now use this route; direct host status remains available if BRAINK is stopped.

An authorized call triggers execution immediately, without another manual command or fabricated completion. This is bounded call-driven actuation, not a new autonomous planning agent. Request IDs originate with callers and must be reused with identical arguments when reconciling a lost response. A retry must not mint a new request ID for an uncertain prior action. Current browser buttons do not automatically retry network failures.

Synchronous callbacks cannot stop/restart their own waiting estate dispatcher; those requests are rejected. The direct owner `action: host` route handles estate lifecycle. Arbitrary URLs, argv, credentials and operations are rejected. Unknown services, stale commands, missing owner authorization and revoked projection agreement do not actuate.

## Existing runtime and rollout targets

Existing admitted family configuration is `.keddeh/family.json`; it targets `/workspace/braink-setup/web4-runtime` and supplies the library manifest, port offset and VFS binding. `.keddeh/launch-family.sh` first invokes `.keddeh/verify-engine.py`, then `scripts/launch_resident_controller.py --manifest .keddeh/family.json`, then `bootstrap_owner_environment.py`. The resident launcher uses the exact image in `.keddeh/CONTROLLER_IMAGE.json`, existing Docker supervision, and the runtime's source/capacity/state configuration. No new physical host is required by this patch.

The existing executable manifest and image identify the earlier qualified engine. A source push does not update them or deploy the new engine. The candidate must be qualified and its wheel/image/executable manifests admitted through the existing release process; do not overwrite hashes to skip qualification. The repository qualification entry point is:

```
.venv/bin/python scripts/qualify_release.py --output /workspace/hosting-qualification
```

It requires the script's pinned uv version and a clean checkout. `scripts/build_resident_image.py --output ... --qualification /workspace/hosting-qualification` builds the qualified image. Those build/promotion steps were inspected, not executed in this task.

Existing prepared package trees need the new derived tool registration. The candidate now supplies a bounded offline migration:

```
PYTHONPATH=src .venv/bin/python -m keddeh_namespace.web4_runtime upgrade-braink --root /workspace/braink-setup/web4-runtime
```

That exact dry-run succeeded: it plans only `packages/estate/server/braink_mcp.py` and `packages/estate/server/host_actuator_adapter.py`. It does not start, stop or change the runtime. Once the existing controller is stopped through its authorized supervisor and the qualified candidate is selected, the apply command is:

```
PYTHONPATH=src .venv/bin/python -m keddeh_namespace.web4_runtime upgrade-braink --root /workspace/braink-setup/web4-runtime --apply
bash .keddeh/launch-family.sh
```

Apply refuses an active controller lock or source-integrity mismatch. It preserves credentials, VFS, journals and desired service state, retains old derived files and launch manifest in a private backup, replaces derived files, and commits their integrity hashes last. An interruption fails closed at `verify_launch`; restore the saved derived files/manifest under the offline lock before retrying. This is not a cross-file atomic transaction or automatic rollback. The apply and rollout commands above have **not** been executed against the existing runtime.

## Published Site boundary

The parent separately observed the native Site's `lib/supervisor-control.mjs` accepting only `https://keddeh.com:3443` or `https://www.keddeh.com:3443` for fixed `start-bind9`. That interface is distinct from this repository's owner WEB4 gateway and BRAINK stdio route. Its current configuration does not establish a general WEB4 connection. These loopback tests do not prove production reachability or deploy the Site. Parent owns Site publication and endpoint/authentication binding; this patch does not add origins, mint credentials or change public routing.

## Executed evidence

The complete Python suite passes 118 tests in the selected environment, including the actual pinned BRAINK archive (no integration skips). `tests/test_braink_host_bridge.py` hydrates the exact estate source, runs its stdio server, runs the real gateway HTTP handler, dispatches start/restart/stop, verifies HTTP bytes and persisted results, retries a duplicate request, rejects stale/unauthorized/revoked/self-dispatch requests, and returns an actual Popen failure. It also verifies offline migration lock/integrity/state preservation and that constructing a controller solely for source inspection does not rewrite active actuator outcomes.

Commands:

```
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
node tests/test_web4_client.mjs
node --check src/keddeh_namespace/web4_client.js
node --check src/keddeh_namespace/web4_panel.js
node --check src/keddeh_namespace/web4_bridge.js
git diff --check
```

The complete owner-family, Docker image build, public network path and live native Site were not deployed or qualified by these tests.

Retention qualification crosses 1,024 commands, replays an archived original without execution, preserves uncertain outcomes, retains hot records on archival failure, and verifies duplicate lookup after signed registry archive/restore. The steady-state hot window is 128; durable history remains in the existing VFS registry.
