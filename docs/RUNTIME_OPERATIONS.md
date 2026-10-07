# Runtime development and operation contract

## Installation and checks

Use the existing checkout; do not create a worktree during cloud onboarding. Python 3.12+ and uv are required. Dependencies are checksum-pinned in uv.lock.

```sh
UV_CACHE_DIR=/workspace/.cache/uv uv sync --frozen --python python
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/test_knot_integration.py
```

The Docker integration test uses an immutable CZ.NIC Knot image digest, an isolated unused private subnet, non-root nodes with no capabilities, read-only roots, bounded temporary filesystems/CPU/memory/PIDs and loopback-only published ports. It generates fixture keys temporarily and removes its containers/network/keys. It does not prove separate production failure domains, port 53 exposure, physical capacity or registrar DNSSEC DS trust.

## Registry

Generate/sign observation envelopes with an authorised Ed25519 key through signatures.py. Keep private keys outside Git and the registry. The trust store maps each identity to a base64-encoded 32-byte Ed25519 public key, explicit roles (generator/verifier) and allowed runtime_ids for generators. Deliver the trust store and checkpoints through an owner-controlled channel. Two identity names backed by the same key cannot independently assess each other.

Provide KEDDEH_REGISTRY_TOKEN securely in the process environment (minimum 32 characters); do not place it in a command argument, repository file or issue. Then:

```sh
.venv/bin/python -m keddeh_namespace.registry_service --root /private/registry --trust-store /private/trust.json --port 8081
```

No production token/key was supplied or requested during local tests. The service binds numeric loopback and requires a bearer token for every route. GET /health verifies the stored history. POST /generations requires exactly request_id, path, expected_version, signed, desired_state and phase_state. Signed observation metric must be registry-generation:<path>. stateRoot/phaseRoot must match the submitted payloads through content_root. expected_version=0 creates a path; later updates require the current version. The per-runtime observation chain must continue from its stored head. Idempotent retries must reuse exactly the same request body. A new request ID cannot replay an existing observation.

GET /generations?path=<canonical-relative-path> returns committed version, digest, receipt and signed generation/data. POST /assessments verifies an independently signed assessment of a committed observation, rejects same-key identity aliases and retains the assessment durably. SQLite WAL/FULL transactions atomically persist generation events, heads, observation chain and idempotency records. Startup/readback checks every signed data/root binding and journal projection.

Use a private operator-controlled storage root. Read-only file modes and SQLite constraints do not protect against a malicious process with the same OS identity. Independent signed checkpoints and trusted assessment are still required for promotion; local receipt hashing alone is not external trust.

## VFS and custody

logical_vfs.py publishes SHA-addressed objects exclusively after fsync and verifies actual readback bytes; path updates use compare-and-swap versions and a chained journal. History never prunes prior generations. A failed database transaction may leave an unreferenced immutable object, but must not alter the committed head.

verify_vfs.py requires a real mount by default and checks observed capacity plus fsync/readback. --allow-directory is local testing only. The current machine has roughly 32 GB total and fails required 10 TB/100 TB capacity gates. Capacity does not prove available space, reserved quota, replication or hardware failure-domain independence; record those separately.

hydrate_service_volumes.py snapshots an O_NOFOLLOW regular source before hashing/extracting; refuses traversal, links/devices, duplicate/reserved paths, encrypted ZIPs and configured file/byte-limit violations. It publishes regular files into write-once SHA-addressed directories, strips writable/special modes and preserves executable bits safely. Repeat admission rebuilds expected content from the exact archive before trusting existing receipt/readback. Deployment manifests must pin the canonical admission receipt SHA, not just trust a mutable receipt file. Filesystem roots must be controlled by the operator; cooperative locks are not a hostile same-user isolation boundary.

The workstation ZIP is a separate source. It is not any of the four REV-002 service archives. Those original archives remain required for service admission.

## Propagation and Genesis

archive_registry verifies the source registry, copies actual generation and assessment bytes to a separate object store and produces a content-addressed manifest. restore_registry prevalidates every object, signature, root, parent, version, assessment and journal head, then replays to an empty registry. On an I/O failure during replay, the target can contain a valid prefix; retain it for diagnosis or retry restoration to a new empty target. Do not promote a partial restore. backward_lineage recovers envelope/source/root identities through every parent; recovering original service source bytes requires those actual archives.

Genesis policy enforces three child identities and two distinct return identities/endpoints per child. probe_returns performs live TCP challenge/readback and verifies authorised signatures bound to child, connection and fresh random challenge. LeaseController persists nonce replay protection, lease bounds, three-active-child ceiling, cooldown and freeze state. Its re-anchor call requires the trusted operator to supply verified recovery; it is not an autonomous proof checker. Real process resource limits and cross-domain continuity remain production integration work.

## DNS staging and preflight

compile_zones.py requires a complete captured inventory and its canonical SHA. Record value contains full DNS RDATA, including MX/SRV priority; TTL, host and type remain separate. It validates zone syntax, retains raw record values and deterministically emits sorted lines. --authority-generation stages explicit NS/SOA/node address changes with an advancing serial; mail and unrelated records remain untouched. It never mutates hosted DNS or registrar delegation.

render_knot_config.py takes two explicit node roles/addresses and external key includes; production refuses missing/non-global addresses or a non-53 port. The primary signs DNSSEC and notifies its TSIG-authenticated secondary; the secondary transfers from its primary. Local testing validates both configurations with Knot itself.

service_stack.py requires all four admitted volumes, trusted admission receipt pins, explicit immutable image digests/argv/routes/ports and ephemeral bounded state. It refuses persistent state until a separately verified quota backend exists. It renders Compose JSON (valid YAML) and an explicit Nginx routing configuration with a default 404. No real service images/entrypoints were invented. The tested Compose fixture is structural-only; no four-service stack has launched.

scripts/bootstrap_runtime_server.sh is a preflight entrypoint, not a completed host population installer. Production requires complete signed gate bundles, trusted keys/heads, bounded fresh observations, artifact hash readback, actual node/archive mounts and direct authoritative UDP/TCP/recursion/transfer/DNSSEC readbacks. Successful preflight reports preflight_passed_not_deployed. Host population, system service installation and actual application launches remain blocked on provisioned hosts and exact sources.

Never claim deployment from local fixtures, configuration or a process ID. Before registrar changes retain full zone custody, stable public addresses, glue/DS plan, independent assessment, change authorisation and rollback window.
