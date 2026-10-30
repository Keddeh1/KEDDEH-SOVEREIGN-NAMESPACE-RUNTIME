# Hosting corrections — local source review

Base: `9bd3152e57d2612e40e700bc1d8e5b8a932fba45`.

## Findings and implemented behavior

- `web4_runtime.py`: the existing native adapter is `LaunchController.spawn`, using guarded subprocesses and existing owned service specifications. `start()` already launches broker, HTTP/R36, network, MCP, ten mesh nodes and outbound agent. Browser routes `/terminal`, `/carrier`, `/research` serve existing KEX sources. Neither broker registration nor a published HTML source proves current browser execution or public reachability.
- Status now reports broker-local registered clients independently from owned processes and browser routes. Zero paired clients is not an empty estate. Unreachable broker reports unknown enrollment. Browser execution and public reachability remain unmeasured by this controller.
- `BOOT_SUBSTRATE` is directory preparation, fsync/readback and runtime binding. The immutable agent is not a Linux or application launcher. API status and queued responses now identify that scope; the panel says “Prepare workspace”. Existing `cloud boot` retains compatibility as workspace preparation.
- `cloud boot OWNED-SERVICE`, or `POST /api/web4/control` with `{"action":"boot","target":"service","name":"<existing service>"}`, runs the existing owned native specification. Unknown names are rejected; no caller-supplied argv is accepted. Alive services retain their PID; exited services use the existing restart adapter; absent processes with a configured specification use spawn. Outputs distinguish process start from readiness. The existing authentication, owner-kernel routing and durable pipeline admission fence still apply. UI service choices come from controller inventory.
- `bootstrap.py` formerly imposed 10 TB per node and 100 TB archive physical capacity regardless of configured backing contract. Logical quota is now separate. Physical `*_backing_required_bytes` and `*_backing_reserve_bytes` policies are optional. Legacy `*_required_bytes` remains an explicit physical requirement; no new field is needed. Without physical policy, preflight measures and executes the existing fsync/readback probe. The example declares only logical quotas. Conflicting legacy/new physical requirements are rejected rather than silently weakened. An earlier candidate required new fields; compatibility review removed that regression.
- `verify_vfs.py` checks physical capacity against physical requirement and available space against reserve plus the 4096-byte probe. Logical quota is recorded, not compared to statvfs. Mount-point checks and fsync/readback remain. This is a point-in-time preflight, not a space reservation or write-time quota enforcement system.

## Persistence and protocol boundaries

Service specifications and process identities use the existing controller lifecycle. This change adds no second process supervisor or state database. Configured specifications are rebuilt by the normal controller startup; it does not persist arbitrary executable commands. Substrate leases retain existing queue/resume behavior. Native service starts do not enter the substrate lease queue. Pending broker leases are not overwritten by this route.

The logical VFS still uses immutable content-addressed objects, fsync, SQLite WAL/FULL, expected-version compare-and-swap and existing recovery. No VFS persistence code or backing reserve policy is weakened. Tests retain source-mutation and symlink rejection, existing lease adoption, receipt recovery and pipeline fencing.

HTTP control remains POST with JSON results; the new service-start operation is locally idempotent for an already alive owned process under the controller lock. This is not a claim that arbitrary POST retries are safe, nor an implementation of HTTP If-Match or 412. Internal VFS expected-version CAS is separate from HTTP conditional request semantics. No systemd dependency or compliance certification is introduced.

## Verification and preservation

Run from the repository:

```
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
node --check src/keddeh_namespace/web4_bridge.js
node --check src/keddeh_namespace/web4_panel.js
git diff --check
```

97 tests passed, including seven new regressions: zero/unknown broker observation, owned service start/idempotence/restart/fencing, real loopback HTTP readback, substrate routing, logical vs physical capacity, physical reserve failure and explicit backing contracts. The suite prints an expected owner-kernel rejection diagnostic while returning OK. System Python initially lacked dnspython; repository `.venv` supplies the declared dependency and all tests pass there.

All ten `PINS` source hashes are unchanged, including agent `0094c4960a208734dc6d783dc5812899928dba9f6d9664ead7c979be046733d5`, estate `c48596dbcb4d826a1172308ab33baf6b52ff76795fce3c62262d4a20b07e5c9e`, HTTP `8718fc7486d73559a3562482245b0fe00acc322b165980c14f1fd03ff3164552`, carrier `2f45e96c5bb5bb20726d03138b2ecb8d14109eff449120b459ca6c68f3c64e31`. Admitted archives and packaged wheels were not edited. Source launch hashing remains active, so deployed derived runtimes need a deliberate rebuild/requalification rather than silent mutation.

No DNS, public routing, domain activation, publishing, credential creation or live deployment occurred. The live browser Linux observation supplied by the parent is not contradicted by broker counts; it was not remeasured here. Complete owner-family startup with all ten source archives and browser UI interaction were not rerun. JavaScript syntax was checked; the new UI controls still require browser integration verification. Existing package copies in other repositories remain unchanged until an explicitly approved release.

`tasks/coding-only-hosting.json` supplies the requested bounded coding task definition. It does not claim to install a model agent: the inspected BRAINK executor is a ring-checked callable executor, and no model adapter has been invented.

## Host/actuator completion

The follow-up is implemented in the same controller, not a replacement host architecture. See `HOST_ACTUATOR_CONTRACT.md` for existing source locations, versioned terminology, callable operations and persistence/retry semantics. The host descriptor is now part of status; the actuator is registered on the existing control route. Browser panel and terminal service operations use descriptor-bound commands. DA remains unresolved.

Current verification: **118 Python tests passed**, plus `node tests/test_web4_client.mjs` passed. All three modified browser JavaScript files pass `node --check`; `git diff --check` passes. Eight additional host-actuator tests cover actual processes and HTTP, lifecycle persistence, duplicate/stale/unknown commands, real spawn failure and a simulated crash after a real process start. The source pin comparison against the original base confirms all ten original hashes unchanged.

Additional boundaries: browser UI was syntax/contract tested, not interactively exercised; the complete original owner-family was not relaunched. No production source, packaged wheels or external registrations were changed. Recorded completed commands are historical; inspect current status for present liveness. A controller crash between dispatch and final persistence yields UNCERTAIN rather than invented exactly-once execution. A fresh operator command after reviewing current state is separate from retrying that uncertain request.

Concurrent qualification also passes: a stop holds the lifecycle lock while a stale start and recovery contend; after stop commits, the stale start is rejected and recovery leaves the service stopped. Controller reconstruction retains the stop. Concurrent duplicate restart requests execute only once and return the same persisted result.

Host mutations reject null pipeline generations and non-integer process IDs; the regression verifies rejection before dispatch or command persistence.

Storage compatibility qualification retains the exact original config.example.json as a fixture. Five regressions cover retained legacy fields, preflight integration without reserve fields, absent-policy logical quotas on small backing storage, original probe behavior without a reserve, and conflicting/invalid explicit policies. No legacy minimum-available-capacity field was found in the inspected source; no speculative alias or migration was added. Mocked mount/capacity and DNS/evidence checks isolate preflight integration; the writable fsync/readback itself is real.

BRAINK integration is implemented and tested through the real pinned estate MCP dispatcher. See `BRAINK_HOST_INTEGRATION.md` for exact ingress/callback/result routes, offline migration and the remaining release/Site deployment boundary. Controller source inspection no longer rewrites actuator state; binding activation occurs only on owning-controller startup.

Retention qualification crosses 1,024 commands, replays an archived original without execution, preserves uncertain outcomes, retains hot records on archival failure, and verifies duplicate lookup after signed registry archive/restore. The steady-state hot window is 128; durable history remains in the existing VFS registry.
