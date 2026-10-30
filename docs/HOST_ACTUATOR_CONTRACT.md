# Existing WEB4 host and actuator contract

Contract `keddeh.web4.host.v1`; binding `keddeh.web4.host-binding.v1`; terminology `keddeh.host-terminology.v1`.

## Existing locations and populated registration

`src/keddeh_namespace/web4_runtime.py` already owns `LaunchController.start`, `spawn`, `restart`, `terminate`, the HTTP gateway and service recovery. `_web4_exec.py` applies Linux process resource bounds before exec. `web4_client.js`, `web4_bridge.js` and `web4_panel.js` are the existing browser-to-native control integration.

The admitted estate source has `host_agent/CONTRACT.json` and `host_agent/kex-host-agent.py`: outbound PAIR/POLL/RESULT, BOOT_SUBSTRATE and DOMAIN_PROBE. The published agent pin is unchanged. Its workspace preparation is not repurposed as process execution. Existing R36 actuation still routes through the HTTP harness. Browser `/terminal`, `/carrier`, `/research` stay browser-local projections; no fake browser VM start/stop transport is claimed.

The controller now registers `action: host` at its existing authenticated `/api/web4/control`. Its existing `/api/web4/status` includes the populated host descriptor. Stable identity derives from the existing runtime generator public key; each controller gets a distinct instance ID. Source digest binds the existing source manifest. Each owned service has a command-specification digest, current PID/exit status, desired state and generation. Runtime initialization writes `state/host-binding.json`; lifecycle commands persist in `state/host-actuator.json`. Neither file contains a new credential. Instances sharing a copied generator identity are distinct through instance binding; no global estate identity uniqueness is claimed.

## Callable operations

Read descriptor: `{"action":"host","operation":"status"}`. Add `name` for a service readback. Status is available when the pipeline is disconnected.

For start/stop/restart, read the descriptor and submit:

```json
{
  "action": "host",
  "operation": "start",
  "name": "http",
  "host_id": "<descriptor host_id>",
  "instance_id": "<descriptor instance_id>",
  "source_digest": "<descriptor source_digest>",
  "request_id": "<unique bounded request ID>",
  "expected_generation": 0,
  "expected_pid": null,
  "pipeline_generation": 0
}
```

Copy generation/PID from the selected service and pipeline generation from the descriptor; example numbers are placeholders, not current values. Browser clients additionally carry the existing projection agreement context. Authentication, owner-kernel routing and pipeline fencing remain in force. `window.KEDDEH_WEB4.service(operation,name)` constructs this binding. Panel actions and `cloud start/stop/restart NAME` use it; `cloud host` reads it. Named `cloud boot NAME` uses start. Legacy raw boot/restart API calls remain supported without the new request replay contract; clients needing replay protection use `action: host`.

Only already-owned specifications may execute. Start leaves an alive service running, or starts/restarts its configured process. Restart replaces the owned process. Stop terminates its process group and durably sets desired state to stopped. Recovery and future startup skip explicitly stopped services. Startup readiness accounts for intentionally stopped mesh services and broker. Stopped dependencies can make other services unhealthy; no automatic dependency restart or application readiness is inferred.

Commands transition ACCEPTED (durably written before dispatch) to COMPLETED or FAILED with observed PID, liveness, exit code and generation. Immediate spawn errors return FAILED. A running process can subsequently fail: COMPLETED means the requested process operation completed, not application readiness or network availability. Status supplies current observation; recorded replay results remain historical.

Exact duplicate command IDs/payloads return the recorded result without execution. Changed payload under the same ID is rejected. Foreign host, stale controller/source, stale service generation/PID and stale pipeline generation are rejected before dispatch. On controller reconstruction, ACCEPTED records become UNCERTAIN and are never automatically replayed. Inspect live state before issuing a new command. No exactly-once guarantee spans process creation and file persistence. The durable request limit is 1024; full retention rejects new commands rather than silently deleting replay protection. A managed archive workflow is not added here.

The gateway's existing controller file lock ensures one controller per root. The existing process lock serializes command dispatch and recovery. Host descriptor reading acquires the pipeline snapshot before the process lock to avoid lock-order inversion against fenced commands. No persisted PID is adopted or signalled after controller restart.

## Terminology v1

| Label | Definition in this contract |
| --- | --- |
| RUNTIME | Execution machinery, such as the KEX browser machinery or native `LaunchController` and guarded executables. A **runtime instance** is one running incarnation with its own instance ID and state. A source archive alone is not a running instance. |
| HOST | An **execution host** supplies the execution context/resources for an adapter. A **network host** is a network-addressed participant; reachability is a separate observation. This descriptor binds the existing native execution context, not a newly required machine. Broker enrollment is only broker-local registration. |
| SERVER | A **server process** handles requests; a **server machine** is the computing resource on which processes run. The controller starts owned server processes and does not provision a machine. |
| LINUX | The Linux kernel; a Linux distribution adds user space. A browser Linux guest executes a kernel and user space through its guest machinery. Browser guest execution is not inferred from a broker record or host OS label. |
| ENVIRONMENT | The configuration, resources, permissions and dependencies within which a runtime instance executes. |
| WORKSPACE | Project files, tools and working state available within an environment. Substrate workspace preparation does not boot a kernel. |
| OPERATOR | An authorized actor exercising operational control in the relevant context. Here it is the authenticated owner under the existing pipeline and projection fences. |
| DA | Unresolved abbreviation; expansion and role await user clarification. No invented definition or actuator privilege is assigned. |
| REGISTRAR | The role/service accepting and managing registrations under an authority's rules. Distinct from a registry database and from an authoritative DNS server serving zone data. This host actuator neither registers nor activates domains. |

## Compatibility and verification

Storage migration: `*_logical_quota_bytes` expresses logical address space. New `*_backing_required_bytes` expresses physical capacity. Legacy `*_required_bytes` remains a physical requirement. Production now requires explicit nonnegative `*_backing_reserve_bytes`; omission fails with a precise migration error. There is no automatic mapping of logical quota to physical allocation. Existing CAS, immutable objects, WAL/FULL, lease checks and recovery remain.

`tests/test_host_actuator.py` exercises descriptor -> fenced dispatch -> actual process -> durable readback, duplicate/stale commands, restart, persistent stop across controller reconstruction, unknown services, actual Popen failure, interrupted outcomes and loopback HTTP reachability before/after restart and stop. `tests/test_web4_client.mjs` verifies client binding and preservation of stale generation fences. These tests do not claim full owner-family, browser guest or public network deployment verification.

Concurrency tests explicitly race stop against a delayed stale start and recovery, then reconstruct the controller to verify the stop remains durable. A second test submits identical restart commands concurrently and verifies one actual restart. The full Python suite currently passes 105 tests.

Host mutations reject null pipeline generations and non-integer process IDs; the regression verifies rejection before dispatch or command persistence.
