# Isolated public host relay client

Candidate only: no credential creation, enrollment, listener, running-target change or activation occurs on installation. The existing admitted runtime and immutable owner archives are unchanged.

Run only after scoped credential approval and exact-candidate qualification:

```
python -m keddeh_namespace.host_relay --root /workspace/braink-setup/web4-runtime --relay-token-file APPROVED_PRIVATE_TOKEN_PATH --state-file APPROVED_PRIVATE_STATE_PATH
```

The state parent directory must already exist. The client reads stable host identity from `state/host-binding.json`, the existing local port from `launch.json`, and local authority from `state/token`. It never copies that local token to the public service. The dedicated relay token is sent only to the fixed HTTPS endpoint `https://www.keddeh.com/api/serverspace/1x/host-relay`; redirects are disabled. Public relay HTTPS preserves the inherited proxy configuration and TLS trust. Loopback gateway requests explicitly bypass proxies. Other destinations are rejected.

Command IDs must be strings matching `[A-Za-z0-9._:-]{8,128}`; claim ID, packet ID and mutation request_id must agree. An operation must be explicitly supplied, including status.

Each claimed JSON-RPC `tools/call host_actuator` packet retains all original descriptor fences and request identity. Dispatch is `action=estate, tool=host_actuator` through the existing local gateway, BRAINK dispatcher and authenticated actuator callback. The complete gateway tool result is wrapped in the original JSON-RPC ID. Unknown operations/tools, incomplete mutation fences, wrong host and oversized packets never reach the gateway. Estate self-mutation remains unsupported by the existing synchronous BRAINK adapter.

An exclusive file lock spans claim, recovery, dispatch and acknowledgement. Private state is atomically replaced with file/directory fsync. After an uncertain local outcome, recovery first reads operation=status/request_id through BRAINK. Only an identical COMPLETED/FAILED command record with a saved result permits reconstruction of the original BRAINK MCP tool response: content contains the sorted JSON text, structuredContent contains record.result, and isError is false, matching braink_mcp.py. Recovery does not resubmit the mutation, so later pipeline-generation changes cannot invalidate the already-persisted outcome. ACCEPTED/UNCERTAIN, absent or inaccessible history remains pending for reconciliation; no new mutation ID is generated. A crash after persisting dispatch_started but before sending the request can therefore require explicit reconciliation of the absent history. Once a result is saved, completion retries never call the actuator again. Completed state remains until the next claim is durably recorded. Authorization/HTTP errors retain pending state and are logged without exception bodies, packet contents or credentials.

Required server semantics: `claim` must return the same outstanding claim to this host when the prior claim response was lost, without issuing the call to another worker. A lease with no automatic reassignment alone is insufficient for that recovery window. `complete` retries must acknowledge the same id/claim/result after a lost acknowledgement. Neither side may invent a new actuator request_id on recovery.

Owner packets, local gateway requests and claim requests are limited to 65,536 bytes. Completion envelopes permit 300,000 bytes, with their JSON-RPC result limited to 262,144 bytes; inbound JSON is limited to 262,144 bytes. If a valid local result exceeds those limits, it is retained intact in private state and completion remains pending. It is not silently truncated or replaced with a fabricated actuator failure. These limits match the isolated public lane contract.

Tests: `python -m unittest discover -s tests -p test_host_relay.py -v`. These cover transport limits, redirect refusal, authorization header, invalid packets, host mismatch, pending-result durability, lost completion acknowledgement and uncertain local replay. They do not claim public endpoint availability or activation.

## Proven rejection versus uncertain outcome

The candidate gateway emits `keddeh.host-rejection.v1` with `effect: none` and one of `AUTH_DENIED`, `ORIGIN_DENIED`, `INVALID_BODY`, `ADMISSION_REJECTED` only at explicit pre-actuation boundaries. Host admission uses a typed exception; pipeline rejection is marked only before entering the execution callback. Generic ValueError/KeyError after controller entry remains an unmarked HTTP400, and other failures remain HTTP502. Neither status alone proves no effect.

The derived BRAINK bridge preserves only this exact bounded marker from the inner gateway; other HTTP errors remain uncertain. On the initial local dispatch, the relay persists a JSON-RPC -32010 error for an explicit marker and completes its lease, allowing the queue to proceed. No fences are refreshed and no new ID is generated. A rejection during history recovery cannot prove the original mutation had no effect and therefore remains pending. This requires deploying the candidate gateway and upgrading the derived BRAINK bridge together before worker activation; the older running gateway does not provide these phase markers.

Public relay requests identify themselves as `Keddeh-Host-Relay/<installed package version>`. This is an application identity, not a browser identity; endpoint, authorization, proxy and verified TLS remain unchanged. It follows Cloudflare Error 1010 guidance for non-browser clients: https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/ .

For descriptor status, tool arguments must be `{"operation":"status"}`. The JSON-RPC envelope ID correlates that read. Supplying `request_id` inside status arguments selects the existing actuator command-history lookup instead; it is not a descriptor-status correlation field.

## Cold-launch admission (2026-10-31)

The repository admission manifest, family engine reference, distributed wheel and controller-image manifest now select exact qualified commit `12ea5441d3b1aac39a30af1960e278bd5a93c7bf` and image `sha256:f53b6e47040cd554173f1a8c833b8ee2ef165768b28257c51180178e2f02ebca`. Verification rules are unchanged. This is a metadata promotion for future cold launches; it does not replace the currently running controller. The active relay already uses that image, while the active controller remains its admitted `3e517a1` image until a future authorized restart.

The retained-state restore qualification started actual native processes and exercised BRAINK/actuator/relay persistence in a network-isolated container without the host Docker socket. It verified identity/history retention, ten healthy nodes, fifteen live native services, intentional-stop persistence across a second start, duplicate-result replay and stale-instance rejection. The public queue was a local fixture in this isolated test; external domain containers and shared VFS publication were not restarted or actuated. See `deployments/receipts/HOST_RELAY_20261031_COLD_LAUNCH.json` for exact scope and live-process continuity.

Existing controller and relay containers have Docker `unless-stopped` supervision. That does not guarantee managed-environment lifetime or recreate deleted containers, credentials or storage. The retained scoped relay launcher and private credential/state directory are required if its container must be recreated. No private snapshot, bearer token or lease credential is included in published receipts.
