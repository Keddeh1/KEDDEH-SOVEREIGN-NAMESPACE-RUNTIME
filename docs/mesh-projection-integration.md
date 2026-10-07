# Mesh projection dependency investigation

The WEB4 status implementation reads actual workstation health, computeCycles and stateHash. These are operational observations, not geometry. The existing browser visualizer contains a separate concept lattice. Neither inspected interface establishes the requested Observer Theorem evolution mapping.

The new mesh_projection.project_mesh(readback, geometry) joins each runtime port identity to one explicit geometry record. It preserves measured counters and rejects missing mappings, duplicate identities, nonfinite coordinates and external service routes. It never maps computation counts to radius or phase by assumption. Geometry source attribution is required. Four focused tests pass locally; their data are fixtures, not production observations.

## Integration sequence
1. Obtain authenticated WEB4 status through the existing owner gateway.
2. Supply geometry from the actual source mapping: origin x/y/z, substratePhase in radians, source reference, and nodes keyed by workstation port with x/y/z, positive loopRadius and local serviceUrl.
3. Run project_mesh. Keep credentials and private source manifests off the public projection.
4. Publish the resulting bounded snapshot through an owner-controlled HTTPS delivery endpoint and configure the website PUBLIC_MESH_URL.
5. Verify a known real state change end to end, including stale and disconnected states, before claiming live execution.

No gateway access checks have been weakened. The adapter is committed software, not a running public publisher. Runtime in the inspected runbook is loopback in a separate workspace; this workspace does not contain that running installation. No public endpoint or verified geometric evolution mapping was discovered in the inspected sources.

## Transport research
https://html.spec.whatwg.org/multipage/server-sent-events.html describes EventSource reconnection and Last-Event-ID; implementing SSE requires an actual event-producing endpoint and cursor/replay semantics, not merely a browser listener.
https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API describes visibility handling; background polling and animation should suspend when hidden.
https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame describes frame scheduling; frame motion alone is not execution telemetry.

Use bounded snapshot delivery first; introduce SSE only once ordered events and resumable cursors exist. Preserve the observation timestamp, source identity and stale-state indication at every hop. The existing website adapter still requires those lifecycle improvements and production binding.
