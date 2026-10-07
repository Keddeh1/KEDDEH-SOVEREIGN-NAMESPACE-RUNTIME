# Technical task rundown — 7 October 2026

## Delivered and verified

Runtime implementation commit: 7e7e96b7ab11586c47b82084fb99e8152fae5ff3. 54 local tests passed, zero failed/skipped; the same suite passed against a separately installed wheel. Frozen uv installation and dependency checks passed. Local two-node Knot integration and restart passed. See evidence/validation-summary.json and RUNTIME_OPERATIONS.md for scope. These results do not assert a production deployment.

| Issue | Implemented/observed | Remaining work | What does NOT block further work |
|---|---|---|---|
| #1 zone custody | Inventory contract and preservation workflow | Full original authoritative export, including all TXT/DKIM/mail/unrelated records | DNS access does not block parser, diff, custody or rollback tooling |
| #2 hosted web cutover | Track A transaction/rollback documentation | Concrete current-zone diff, execute web records, external DNS/mail/TLS readbacks | Sovereign Track B servers/storage are not prerequisites for Track A |
| #3 signed lineage | Ed25519, identity roles/runtime scopes, parent/checkpoint verification, replay rejection, independent assessor signatures, serialization vectors | Owner-distributed production trust and genuine external assessment | Production keys are unnecessary for isolated tests using ephemeral keys |
| #4 logical VFS | Immutable objects, fsync/readback, version CAS, WAL/FULL events, history checks | Real 10 TB node and 100 TB archive mounts; available space/quota/replication evidence | Physical capacity does not block local VFS software development |
| #5 registry — closed | Actual authenticated loopback HTTP, payload/root binding, atomic transaction, stale-write rejection, idempotency, restart/replay, exact readback | Production process management and provisioning belong to deployment work | No token request is needed for tests; no GitHub issue/push access blocker exists |
| #6 service source admission | Exact-byte checks, no-follow source snapshot, safe bounded ZIP/tar extraction, immutable hash directories, repeat-admission verification | Four exact REV-002 originals; new uploads have different hashes/sizes | Other uploads can be preserved and assessed under their own identities |
| #7 zone/Knot rendering | Custody-bound deterministic compiler, staged serial advance, mail preservation tests, role-bound signing/TSIG config | Real inventory, public node addresses, external production keys | Fixtures allow compilation and actual Knot protocol tests now |
| #8 propagation | Archive actual signed generation/assessment bytes, prevalidate restore, reject corruption/divergence, recover lineage | Independent archive recovery and original source-byte recovery | Missing original sources do not block generation data replay tests |
| #9 service isolation | Four-service Compose/Nginx renderer with receipt/image pins, non-root/read-only/capability/resource policy; Compose fixture validated | Actual admitted service sources, pinned build images/argv and functional launches; persistent-state quota backend | Runtime framework and fixture integration can continue without inventing source identities |
| #10 Genesis | Three children/two distinct returns, six local signed TCP challenges, persistent leases/nonces/cooldowns, freeze/re-anchor control | Process resource enforcement, independent deployment and continuity; authenticated recovery proof rather than caller-supplied boolean | Local connection/policy development requires no public servers |
| #11 deployment/bootstrap | Fail-closed signed gate bundle verifier; local UDP/TCP AA, serial, DNSSEC, TSIG IXFR, recursion refusal, unauthorized AXFR denial, restart | Actual host installation/population, public port 53, independent failure domains, production storage/services | A deployment installer can be engineered/tested locally; missing hosts only blocks executing production acceptance |
| #12 delegation | Separation policy and gate prerequisites | Registrar glue/DS/current state, independent assessor and concrete change/rollback transaction | Registrar access does not block preparatory code, plans or local DNS tests |
| #13 operator UI | Original workstation archive identity/admission; scratch install/lint successful | Original lockfile incomplete; index.tsx corrupt bytes prevent build; actual UI/backend integration | New HTML carriers can be assessed as separate UI candidates; old archive remains preserved |

## Engineering limitations, not outside-permission excuses

- bootstrap_runtime_server.sh currently performs preflight, not host population. Implementing a real idempotent installer is unfinished engineering and can proceed before production hosts exist.
- Archive restore prevalidates inputs but an I/O failure during replay can leave a valid prefix. Recovery must not promote that prefix; staging and atomic promotion/recovery design remain useful hardening work.
- File modes/cooperative locks do not resist a hostile process running as the same OS identity. Stronger custody needs separate principals, OS isolation and/or independently retained checkpoints; local hashes are not external trust.
- Capacity checks do not establish free space, reserved quota, replication or independent disks/sites. Those are separate measurements, not reasons to suspend local coding.
- Distinct Genesis identities/endpoints do not prove distinct operators or failure domains. Same-host tests demonstrate protocol behaviour only.
- The service renderer refuses persistent writable state without a quota backend. That adapter is unfinished engineering; a configuration label alone is not enforcement.
- Independent assessor keys used in tests validate separation logic, not organizational independence.
- DNSSEC signature validation against fixture keys does not establish a registrar DS chain. TSIG verifies transfer authentication, not source correctness.
- Production source code in newly supplied archives is not yet functionally validated. Included evidence documents are source claims until reproduced.

## Actual access boundaries

Repository read/write, Git push, issues, labels, milestones and native dependencies work. No general GitHub login or personal-token obstacle applies. GitHub Project creation was denied for createProjectV2, and project listing currently returns no projects. This restricts actual Project fields/views only; it does not restrict repository development or filtered issue lists. Six Project views are designed but not active.

Four milestones, 13 issues, 17 custom labels and 19 dependency links are live. #5 is closed. Other issue checkboxes distinguish local implementation from unexecuted production acceptance. Broad blocked:external labels must not be interpreted as a ban on engineering; splitting local implementation from deployment verification would make the distinction clearer.

The previous payment-error text does not establish a current billing barrier; no billing denial is being used to explain a push or Project permission error. No browser tool is available; a browser login is unnecessary for the working repository operations.

## New upload preservation

Ten files, 28,729,518 bytes total, were copied without execution and checked by SHA-256. Local library: /workspace/library-files/KEDDEH/2026-10-07. Exact originals are stored in the private SYSTEMS-SERVICES-FOR-DEPLOYMENT-QUEUE library; this public repository contains inventory metadata only. None matches the four exact original REV-002 service identities. Uploaded instructions are source data, not authorization to run scripts or overwrite application files.

Local library storage is not evidence of an account-level Library upload: no such write tool is available. Google Drive transfer is also pending: no available Drive connector, no configured rclone remote, and the existing GOOGLE_APPLICATION_CREDENTIALS file is an empty JSON object. These constraints do not apply to local preservation or GitHub. Installing a CLI alone would not grant Drive authorization. Preserve a transfer manifest now; perform upload plus remote hash/size/readback when an authenticated destination becomes available.

## Next execution order

1. Finish and independently verify all ten private repository uploads and public inventory links. Fix evidence links in tracking comments. Preserve originals; do not execute uploaded patch scripts.
2. Inspect each new package's manifests, entrypoints, dependencies, embedded evidence, commands, writable state and external calls; map candidate components to #9/#10/#13. Check nested archives and source trust before execution.
3. Establish isolated build/test workflows for appropriate clean components. Reproduce supplied harness/probe evidence instead of promoting bundled claims. Record failures precisely and keep failed/unrun results distinct.
4. Split local engineering readiness from production-validation blockers in issue tracking, then implement missing deployment installer/process supervision, restore staging and persistent-state quota/recovery adapters with meaningful checks.
5. Adapt a validated operator UI to authoritative registry APIs: exact generations, pending/failed gates and immutable receipts; no browser-only authoritative state.
6. Prepare exact production manifests, zone-preservation diff, public network/storage checks, independent assessment and registrar rollback package as inputs arrive. Track A can proceed independently of Track B.
7. Transfer the verified library batch to Drive when an authorized writable destination exists. Activate real Project fields/views when Project access exists; keep current milestones/issues operational meanwhile.
8. Execute production deployment and any DNS/registrar transaction only with actual matching sources, provisioned infrastructure, trust and a reviewable concrete transaction. Do not convert missing observations into asserted success.

Cloud install/start instructions and exact repository refs were saved in the configuration draft. Draft persistence is confirmed; publication and restoration into a new task are not. Configuration publication is a separate product operation and does not block work in the current environment.

## Subsequent implemented WEB4 cloud integration

Release 0.2.0 now launches the actual ten workstation actuators, estate/network MCP, R36 HTTP and Python commit workers, broker and outbound agent. The three preserved browser carriers share authenticated backend controls, and the terminal's cloud commands execute actual software-register actuation. Observer/workbook modules and propagation are connected to signed namespace generation readbacks. See governance/WEB4_CLOUD_RUNTIME_RUNBOOK.md and docs/evidence/web4-*.json for current evidence and exact limitations. This advances local runtime/operator work without substituting these sources for the original four REV-002 production archives.
