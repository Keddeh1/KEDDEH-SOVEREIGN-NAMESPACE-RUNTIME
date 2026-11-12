KEDDEH SYSTEMS | RESEARCH AND FORMAL PUBLISHING  
ENGINEER · AUTOMATE · SCALE

# Registering the 08F self-host worker in the owned WEB4 controller

Document: KEDDEH-ENG-HOST-REGISTRATION-001 | Version: 1.0 | Classification: Engineering | Status: Draft  
Author: Aboudy Keddeh, Systems Architect | Publisher: Keddeh Systems  
Contribution: ChatGPT source inspection, implementation and local qualification. No independent production assessment.  
Date: 13 November 2026, Australia/Adelaide

## Implemented contract

The namespace runtime can register the pinned 08F v2.1 outbound worker as `keddeh-field-08f.service`. This is an optional extension of the existing `LaunchController` registry. It does not pair a node, start a process, adopt a PID, submit an actuator request or change the protected dispatch.

`LaunchController.start()` calls `register_configured_08f()` before host-binding activation and before any process spawn. An absent `field_08f` configuration retains the existing service set. A present but incomplete or invalid configuration rejects startup before activation. Successful registration adds the existing registry tuple `(argv, cwd, extra, stdio)`; a subsequent start still requires the existing authenticated, descriptor-bound owner actuator.

The helper verifies the stable target host, exact source-manifest entry and on-disk source hash. It requires an existing absolute enrollment file, an existing absolute workspace, a positive protocol sequence and an HTTPS broker origin. It rejects the standard agent's enrollment, symlinked enrollment/source, hard-linked enrollment collisions, mutable state inside the read-only package volume, conflicting service specifications and a process without an owned specification. Exact repeat registration preserves the same specification and enrollment bytes.

The registration is specific to host `web4-2d5eefa3698ab755ed10237462171cf472675b83e0aa01994a817f3164ed1f8d`. No new host identity or credential is created.

## Exact package custody

| Object | Bytes | SHA-256 |
|---|---:|---|
| `Keddeh-Self-Host-Node-08F-v2.1-Candidate.zip` | 51,837 | `6f1b502500ae971bc067f416aaa7e9f353bd08424f5c2d262c86899a013d4f21` |
| Separate JSON source overlay | 78,977 | `e975da4c651a9db462ee12b47fabfc21dbf4dfaa135c04c54509ab6ab4cc52cf` |
| `08F_kex_self_host_node_v2_1.py` | 59,125 | `7f6435c183f444fbf1913028cec4bc94795528b7c334b02c55edf79d359a4eb9` |

The 78,977-byte value identifies the overlay, not the ZIP. The recovered archive has eight regular members and a valid CRC; the overlay's four embedded files match their ZIP counterparts. `docs/evidence/FIELD_08F_CANDIDATE_CUSTODY.json` retains the member identities. This change does not alter or republish the implementation bytes from that owner package.

The installed entry belongs at `packages/08f-v2.1/08F_kex_self_host_node_v2_1.py` beneath the existing runtime root. Merge the eight mappings in `docs/examples/field-08f-launch-files.json` into the existing `launch.json.files` after installing and checking the exact package. Preserve every earlier file mapping and source record. Do not replace a populated runtime root or its existing state.

## Explicit existing state and host bindings

The configuration shape is:

```json
{
  "field_08f": {
    "state_file": "<observed absolute path to the existing 08F enrollment file>",
    "pass_host_env_names": [
      "BRAINK_MCP_HMAC_KEY_HEX",
      "KEX_RECEIPT_HMAC_KEY_HEX",
      "BRAINK_MCP_DATA_DIR"
    ]
  }
}
```

The placeholder deliberately fails validation. The actual path must come from the intended host. `state_file` is required when the object is present. `pass_host_env_names` is optional and defaults to no forwarding. It is a distinct list of names from precisely the three shown above. Secret values are never accepted in this configuration. Requested bindings must already exist in the trusted host launcher's environment; HMAC keys require at least 32 bytes of hexadecimal input and the data directory must be absolute.

The resident launcher accepts the same optional `field_08f` object in its family manifest and preserves existing runtime configuration when that object is omitted. It forwards requested variables through Docker using `--env NAME`, then the controller passes those values only in the 08F service's `extra` environment. Ordinary service environment filtering remains unchanged. Values do not appear in Docker argv, launch JSON or registration results. If an existing same-image container has different requested values, launch rejects before stop/recreation and requires explicit container reconciliation with its state retained.

The enrollment file, writable parent, workspace and any configured data directory must be accessible in the existing controller mounts. This change does not invent mounts or discover private paths. The existing 08D Port 8810 service requires the MCP HMAC binding; merely registering or starting 08F does not prove Port 8810 ownership.

## Executable admission and qualification

Runtime version 0.3.3 carries the helper in the normal Python wheel. The prior executable manifest is retained as `docs/evidence/FIELD_08F_PREDECESSOR_EXECUTABLE_MANIFEST.json`; the predecessor wheel remains in repository history and under its previous versioned name.

The repository's `.keddeh/verify-engine.py` rules remain unchanged: exact admitted source hashes, no unlisted Python/JavaScript engine modules, and an exact distributed wheel digest. The regenerated executable manifest admits the qualified source commit `d9f81260ec0d8276c72675e7d57f815b9f872cb8` and the actual 0.3.3 wheel, 86,299 bytes with SHA-256 `a93da90a5758a87f07907f3f226bd2db6e73be6e54131305a60e0d77a5a7c826`. The unchanged verifier passed against the 40-entry source inventory and retained wheel; all 34 engine source files in the wheel also match their source bytes.

The controller-image record remains the predecessor record for commit `12ea5441d3b1aac39a30af1960e278bd5a93c7bf` and its 0.3.2 wheel. It is not an image admission for this change. Docker CLI and the Docker socket are unavailable in the qualification executor. A new image built from the qualified 0.3.3 wheel, independently verified image metadata and actual host runtime qualification remain required before promotion. No image, deployment or Port 8810 ownership receipt was produced.

The existing qualification runner uses `uv 0.12.19`, frozen dependencies, source tests, a wheel built with pinned build constraints, and a separate installed-wheel test environment:

```sh
python scripts/qualify_release.py --output /absolute/new/evidence-directory
```

Its output directory must be outside the checkout. Runtime and browser integration require the independently supplied `--runtime-root`; ordinary source/wheel qualification does not create a deployment receipt. The new targeted tests execute the actual controller registration/start paths with synthetic owner state, and test the actual resident-launcher command construction with a simulated Docker response. They do not pair with a live broker or execute Docker lifecycle operations.

All nine local qualification gates passed. Both the source suite and the independently installed-wheel suite ran 156 tests: 153 passed, with three existing BRAINK integration tests skipped because the pinned owner estate archive was unavailable. The 25 added registration and resident-binding regression tests passed in both suites. The report, complete logs, dependency inventory and skip accounting are retained under `docs/evidence/field-08f-registration-20261113/`. This result qualifies source and wheel bytes; it does not approve production operation. The earlier local-source qualification is retained under `predecessor-local/`, with `source-lineage.json` proving that its source tree equals the published source tree. The manifest admits the newly qualified published commit and its actual rebuilt wheel; the prior local wheel remains historical evidence.

## Runtime and evidence boundaries

Registration reconstructs the specification after controller reconstruction. It does not automatically resume an unstarted worker: `recover_services()` traverses owned process objects, not specifications alone. Use a fresh host descriptor and service readback for the eventual explicit start.

08F's Layer-04 result envelope uses HMAC-SHA256. The separate 08D service exposes its existing MCP ledger and seed checks. Neither source currently invokes the R8/R10 admission library or issues physical A/B Ed25519 evidence. This registration extension makes no R10 repository or deployment claim and does not translate a process/HTTP observation into KVR1 or an A/B receipt.

`KEX-DISPATCH-AA40B63A9FC6022C5102` remains unchanged. Start fences, observed PIDs, generations and process completion must come from current execution receipts.

## Sources and revision history

- Namespace source: `Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME`, branch `fix/hosting-semantics-20261030`, base `3096cf880ee2b9aec8eebb2f1d4ab13dce76cbf4`.
- Existing controller/actuator contract: `src/keddeh_namespace/web4_runtime.py`, `docs/HOST_ACTUATOR_CONTRACT.md` and `docs/HOST_RELAY_CLIENT.md` at that base.
- New implementation: `src/keddeh_namespace/field_08f_registration.py` and the existing controller/resident-launcher call sites.
- Regression evidence: `tests/test_field_08f_registration.py`, `tests/test_field_08f_resident_bindings.py` and the retained qualification report.
- Version 1.0: optional registration, existing-state and source gates, narrow host-environment forwarding, synthetic regression fixtures and preserved admission provenance.

© 2026 Aboudy Keddeh. Published by Keddeh Systems. KEDDEH-ENG-HOST-REGISTRATION-001 | v1.0 | Engineering | Draft.  
KEDDEH-RESERVED-1.0. All rights reserved. No licence is granted by this document. Separate written permission governs reuse, redistribution and implementation, subject to applicable law. Third-party material retains its own rights.
