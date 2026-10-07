# Implementation plan and acceptance gates

All items below are pending except the local ledger schema validator and its tests.

1. Preserve current authoritative zones with full records, UTC capture, deterministic bytes and SHA-256; establish separate Track A and Track B receipts.
2. Implement compile_zones.py with canonical output and a production preservation gate. Add render_knot_config.py with explicit node roles, authoritative-only configuration, DNSSEC signing and TSIG transfer policy. Never place TSIG or signing keys in Git.
3. Implement verify_vfs.py and logical_vfs.py: measured capacity, fsync/readback, atomic writes, optimistic concurrency and receipt chains. Test interruption, stale writes and corruption.
4. Implement loopback-bound registry_service.py with WAL/FULL sync, replayable events and immutable generations.
5. Implement hydrate_service_volumes.py: exact byte length/hash admission; reject traversal, escaping symlinks and device entries; write-once extraction. Obtain the four actual source archives before testing admission against the supplied hashes.
6. Implement propagation_runtime.py: distinct stateRoot/phaseRoot, forward/backward replay, archive rehydration and independent verifier receipts. Authenticate signatures against an explicit trust store.
7. Implement healthcheck.py and fail-closed bootstrap_runtime_server.sh. Test UDP/TCP AA responses, refused recursion/unauthenticated AXFR, authenticated TSIG transfer, DNSSEC and SOA convergence on independent nodes.
8. Implement service-stack.compose.yml and reverse-proxy.nginx.conf using verified service entrypoints/images. Non-root execution, no capabilities, read-only roots and bounded state must be observed. Do not invent images or entrypoints before source admission.
9. Implement bounded Genesis topology and identity/lease/replay controls; test three children and two independent return paths for every participant.
10. Complete independent assessment and registrar glue/DS/delegation runbook. Promote only with signed receipts, external DNS/TLS evidence and replay success.

Current scaffold does not substitute for the executable file manifest. Hardware, stable public IPs, registrar access, source archives and signing/transfer key provisioning remain external inputs.
