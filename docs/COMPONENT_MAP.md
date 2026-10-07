# Uploaded source component map

## Scope and evidence

Static inspection only: no uploaded module was imported, no setup/deployment command inside an attachment was executed, and no source was integrated. File sizes and SHA-256 identities are recorded in UPLOAD_INVENTORY.json. Definitions, selected code paths, ZIP metadata and PDF text were inspected. This is a component assessment, not a complete code audit or runtime validation. Instructions inside the uploads remain document content.

## Implied model

The research treats an occupied substrate state as distinct from the observer's reference coordinates. The PDF describes origin 1 with bilateral relations and an observer displacement mapping rho; zero displacement is allowed as a measurement while zero is not an addressable native state. Its proposed addition is defined through rho and its inverse. This is a representational model, not evidence that ordinary arithmetic, physical storage, authentication or network protocols have changed.

For the namespace runtime, carry this distinction into explicit identities and evidence: source/object identity persists; observer, metric, execution plane and timestamps qualify measurements; transformations retain parent state rather than erase custody. Keep source identity, stateRoot, phaseRoot and observations separately represented. Do not forbid numeric zero in standard DNS, operating-system or storage interfaces. Native state labels need an explicit adapter when crossing those interfaces.

## Map by upload

| Source | Candidate role | Inspected evidence | Reuse decision and required work |
|---|---|---|---|
| ORIGIN OF ZERO PDF | Conceptual state/observer model | Occupied origin, bilateral relation, rho displacement mapping, proposed native addition | Architecture reference. Define schemas and testable transformations before implementing native label semantics. No physical or deployment claim follows from this text. |
| untitled0.py | Non-erasing transforms and receipt lineage | KEXStateKernel, H2OWholeState, NonErasingArithmeticLibrary, repeated ProofLedgerHashChaining; final chain implementation near line 1728 | Extract one canonical version into a separate implementation task. Existing chain is mutable/in-memory, uses naive local timestamps, accepts caller-selected parent hashes and does not validate genesis in is_chain_valid. It needs canonical serialization, immutable storage, genesis validation, signatures, durable replay and independent assessment. |
| k_cloud_substrate_master_daemon.py | Admission/router and recovery orchestration | SovereignHardgate at 734, ZeroLessIndexEngine at 752, DynamicHealingAgent at 770, KCloudNode at 791 | Simulation/reference. Hardgate checks a marker substring and an always-defined arithmetic result; it is not cryptographic authentication. Router returns a formatted slot string, and 26-node traversal sleeps then sets a status. Neither proves hardware mapping or service health. Whole file fails parsing at 348. |
| colab_substrate_mount.py | Operator surface and cloud-storage adapters | Repeated _process_ai_prompt, _trigger_sovereign_task and _list_substrate_files; Colab callbacks and storage references | Environment-specific reference. Parsing stops on notebook syntax at 286. Separate UI callbacks, configuration and portable storage adapters; deduplicate revisions and remove import-time operations before reuse. |
| get_started_managed_agents.py | Optional managed-agent integration | Colab/Google GenAI imports and managed_agents references; parses, no top-level function/class boundary | Optional provider adapter, not a prerequisite for authoritative DNS. Isolate notebook demonstrations behind explicit invocation; establish provider credentials, bounded execution, identity and audit before running. |
| copy_of_untitled3.py | Genesis topology/recovery simulation | ResonatingNode at 2037 and TriadCluster at 2066, three clusters of three nodes, random drift and scalar recovery | Useful experimental topology reference. It does not implement exactly three child domains per genesis participant or two independent return connections per child. No actual sockets/lease enforcement or restore evidence in the inspected model. Parsing fails with an unterminated string at 64. |
| bilateral_discrepancy_solver.py | Phase simulation and quorum envelope ideas | StochasticKuramotoPLL at 54; VFSChunkPayload at 1099; ClusterHMACFabric at 1111 | Review isolated algorithms in a separate task. HMAC checks can verify holders of shared keys, but do not establish independent assessor signatures or Byzantine agreement. Unknown signer IDs can raise KeyError; f=1 requires three signatures, incompatible with treating only ns1/ns2 as a sufficient quorum. Notebook syntax fails parsing at 9660. |
| workstation + BRAINK ZIP | Operator application, API contracts, browser storage and failure outbox | React/Express/Vite package; src/kernel/registry.ts, failure-ledger.ts, root-registry.ts, state-deriver.ts, src/vfs-recovery.ts, proto/atomic_ledger.proto, node-registry-api.yaml | Best application candidate, with distinct source identity. Use interfaces and UI concepts selectively. Do not adopt its browser state as authoritative node registry or production archive without backend contracts and tests. |

## Workstation findings that change the mapping

- root-registry.ts is a singleton registry for React rendering roots. It does not register sovereign namespace roots or DNS authority.
- registry.ts stores application manifests in an in-memory Map and boots tiers through DOM-bound methods. It has no SQLite WAL/FULL durability, compare-and-swap generation check or server-side replay in that implementation.
- failure-ledger.ts stores browser IndexedDB events and an outbox. It mutates/deletes resolved events and resolves writes on request success rather than transaction completion. Reconciliation invokes the handler before marking completion, so retry can repeat side effects without an idempotency contract. Retain the outbox concept; require durable immutable audit events and idempotent server operations.
- state-deriver.ts returns constant labels for some invariants and Math.random-based labels otherwise. These are not deterministic content hashes and cannot serve as stateRoot or phaseRoot.
- vfs-recovery.ts records supplied block hashes and copies the last eligible hash during recovery. It does not read blocks, recompute hashes, validate the baseline, fsync or measure capacity. Its 256-entry/64-byte-path bounds are useful schema ideas; actual archive restore remains unimplemented there.
- atomic_ledger.proto defines parent/hash/signature fields but its events are financial transactions. A schema is not a signing/verifying implementation. A namespace envelope needs separate runtime/source/generation/observer/command/readback fields and distinct roots.
- node-registry-api.yaml offers liveness/readiness, nodes, manifests and failures as an interface starting point. Described endpoints and response examples do not prove an implemented service or authentication.
- ADR-005 describes IndexedDB directory readback. Browser quota and directory existence do not establish either 10 TB node plane or a 100 TB archive.

## Exact-source boundary

The workstation ZIP is 3,312,374 bytes, SHA-256 7d39b6f1941bc447f4afd498243c6171cd6231b8d117b1e228c5550b214de002. It matches none of the four REV-002 archive size/hash pairs. Register it as an additional input, never relabel it as StoreSpace, ServerSpace + Mine, BRAINK full or BRAINK light. Those original archives remain missing.

## Suggested implementation order

1. Adopt a versioned identity/observation envelope and explicit origin-label adapter specification. Maintain ordinary protocol semantics at DNS/storage boundaries.
2. Build canonical immutable receipts and verify genesis, full parent chain, signatures and trusted assessor separation. Use the Python ledger only as a teaching reference.
3. Implement the server-side durable registry and logical VFS; borrow browser outbox/UI concepts behind those APIs. Test transaction aborts, stale writes, corrupted blocks and idempotent retries.
4. Build bounded Genesis topology with real participant/child/return identities, leases and independent connection readback. Keep stochastic phase experiments separate from health evidence.
5. Integrate the workstation as an operator application only after source admission and package validation. Isolate optional Colab/managed-agent adapters.
6. Implement and independently test Knot authority, DNSSEC/TSIG and delegation gates. The inspected candidates do not supply executed evidence for these requirements.

No uploaded candidate establishes live authoritative DNS, stable public addresses, exact required service archives, measured node/archive capacity, or independent DNS/TLS promotion. Those remain separate acceptance work.
