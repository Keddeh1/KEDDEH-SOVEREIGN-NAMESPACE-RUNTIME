# Isolated public host relay client

Candidate only: no credential creation, enrollment, listener, running-target change or activation occurs on installation. The existing admitted runtime and immutable owner archives are unchanged.

Run only after scoped credential approval and exact-candidate qualification:

```
python -m keddeh_namespace.host_relay --root /workspace/braink-setup/web4-runtime --relay-token-file APPROVED_PRIVATE_TOKEN_PATH --state-file APPROVED_PRIVATE_STATE_PATH
```

The state parent directory must already exist. The client reads stable host identity from `state/host-binding.json`, the existing local port from `launch.json`, and local authority from `state/token`. It never copies that local token to the public service. The dedicated relay token is sent only to the fixed HTTPS endpoint `https://www.keddeh.com/api/serverspace/1x/host-relay`; redirects and environment proxies are disabled.

Command IDs must be strings matching `[A-Za-z0-9._:-]{8,128}`; claim ID, packet ID and mutation request_id must agree. An operation must be explicitly supplied, including status.

Each claimed JSON-RPC `tools/call host_actuator` packet retains all original descriptor fences and request identity. Dispatch is `action=estate, tool=host_actuator` through the existing local gateway, BRAINK dispatcher and authenticated actuator callback. The complete gateway tool result is wrapped in the original JSON-RPC ID. Unknown operations/tools, incomplete mutation fences, wrong host and oversized packets never reach the gateway. Estate self-mutation remains unsupported by the existing synchronous BRAINK adapter.

An exclusive file lock spans claim, recovery, dispatch and acknowledgement. Private state is atomically replaced with file/directory fsync. After an uncertain local outcome, recovery first reads operation=status/request_id through BRAINK. Only an identical COMPLETED/FAILED command record with a saved result permits reconstruction of the original BRAINK MCP tool response: content contains the sorted JSON text, structuredContent contains record.result, and isError is false, matching braink_mcp.py. Recovery does not resubmit the mutation, so later pipeline-generation changes cannot invalidate the already-persisted outcome. ACCEPTED/UNCERTAIN, absent or inaccessible history remains pending for reconciliation; no new mutation ID is generated. A crash after persisting dispatch_started but before sending the request can therefore require explicit reconciliation of the absent history. Once a result is saved, completion retries never call the actuator again. Completed state remains until the next claim is durably recorded. Authorization/HTTP errors retain pending state and are logged without exception bodies, packet contents or credentials.

Required server semantics: `claim` must return the same outstanding claim to this host when the prior claim response was lost, without issuing the call to another worker. A lease with no automatic reassignment alone is insufficient for that recovery window. `complete` retries must acknowledge the same id/claim/result after a lost acknowledgement. Neither side may invent a new actuator request_id on recovery.

Owner packets, local gateway requests and claim requests are limited to 65,536 bytes. Completion envelopes permit 300,000 bytes, with their JSON-RPC result limited to 262,144 bytes; inbound JSON is limited to 262,144 bytes. If a valid local result exceeds those limits, it is retained intact in private state and completion remains pending. It is not silently truncated or replaced with a fabricated actuator failure. These limits match the isolated public lane contract.

Tests: `python -m unittest discover -s tests -p test_host_relay.py -v`. These cover transport limits, redirect refusal, authorization header, invalid packets, host mismatch, pending-result durability, lost completion acknowledgement and uncertain local replay. They do not claim public endpoint availability or activation.
