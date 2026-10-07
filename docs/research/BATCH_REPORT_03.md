# Batch 03: crash recovery and full resident family deployment

Steps 21–30 are completed with ten result artifacts, owner VFS actor/byte readback,
ten real R36 transactions, separately executed signed journal verification and
ninety mirrored result copies across all nine families. Isolated power-loss tests
use clearly identified actor fixtures; real R36 journal behavior is separately
qualified. No independent production assessment is claimed.

The final executable baseline is `9ab5fd83c4e3e87e592885f00e912f2d8fe19233`, release
0.3.2, wheel SHA-256 `5bbaad7c3d4c2dee231255eb183343674e48a6411f7ee007118c78b3dfffe71d`.
Twelve release gates passed: frozen install, dependency check, governance, ninety
source tests, build, isolated installation, ninety installed-wheel tests, installed
dependency check, sixteen live checks, six Chromium checks and six domain checks.
The exact same wheel also passed ninety tests installed into the resident image.

## Failure corrections

- Retained nonces and saved acknowledgement prefixes reconcile register commit
  before acknowledgement. Pre-intent and post-intent crash experiments distinguish
  no published intent from a retained ten-command intent.
- Stable pending-cycle identity reconciles namespace commit before cycle-state
  save. Restart returns the original receipt even after an intervening launch
  generation; changed data under the same identity is rejected.
- Explicit pause and feedback loss preserve unfinished state and prevent invalid
  new actor calls. A separate outage/restoration experiment recovered correctly.
- Domain memory policy is permanently 256 MiB with bounded worker/probe heaps,
  not just a temporary Docker update. Existing admitted domains receive the policy.
- Startup/domain budgets distinguish quick health probes from longer operations.
- Existing boot leases are adopted on controller restart rather than replaced.
- A named image user supports the supplied agent's home-directory lookup without
  changing HOME or modifying the original owner agent.
- All nine host controllers are now supervised resident containers, alongside
  twenty-seven recursive domains and 171 owner workstations.

## Live crash qualification

The canonical controller's verified process handle was killed unexpectedly. Docker
restarted it: host PID 132391 became 173652; restart count zero became one. Ten
healthy nodes and completed boot returned. The signing key, agreement bytes and
durable disconnect were retained; no new HTTP actor journal bytes were observed
while disconnected. The owner pipeline policy was restored after qualification.
This proves the current-host case, not host/daemon/mount loss or an off-site SLA.

## User/service boundaries

All three preserved HTML surfaces expose projection placement, service terms,
versioned owner-space acceptance, revocation and family-scoped disconnect. The
software fence does not undo committed work, block direct trusted raw-actor callers
or firewall the host. Customer registration remains separate from owner tokens.
Off-site observation has no configured host or actor credentials.

## Packaging, attribution and standardization

Both private VFS repositories retain the full source/wheel/owner-original bundle.
The 0.3.2 bundle digest is `5857359830b8c24e9028c3dda7287d62ca0c7ad0803c32e0b6fc0adfe6577dc6`;
its exact bytes were admitted and observed in owner VFS and mirrored by all nine
families. Additional documentation revisions are separately identified and do not
change this historical bundle digest.

The architecture specification, data/attribution contract, technology assessment
and standardization audit are linked from `docs/ARCHITECTURE.md`. ARC-001 adds a
controlled standard with owner-directed issuance and independent review pending.
Package documentation now covers nineteen actions, twenty-three process roles,
sixteen configuration groups and 149 source functions/methods. Architecture decision,
service-boundary and file-attribution templates supplement existing control records.

## Remaining gates and next work

Nine families share one physical host, Docker authority and owner VFS hub. Native
Projects creation remains explicitly denied by integration; hosted VFS startup
failed before jobs without an established current provider cause. Native Site/Drive
publishing tools are unavailable. No claim of worldwide novelty, physical power,
independent certification, general multi-tenant isolation or deployed off-site
security is supported by this delivery.

**Next task: step 31 — evaluate recursive-domain capacity and continuity limits, then execute steps 31–40 with measured resource and failure evidence.**
