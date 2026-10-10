# BRAINK owner-state continuity — 1.0

Author: Codex, engineering assistant. Source state: owner-supplied Keddeh carriers. Publisher: prepared for Keddeh Systems. Rights holder: existing owner rights retained; no transfer. Licence: reserved rights pending owner designation. Classification: local engineering implementation and verification. Status: executed locally; no independent or production certification. Date: 10 October 2026 (Australia/Adelaide).

This package treats supplied material as exact source state. It does not substitute external algebra for owner declarations. The downloadable archive includes complete carriers, identities and durable lineage in owner-state-vfs. Repository tooling omits the private source carriers: ingest both files under the two identities shown in server.py before launching it. The lexical projection is separately identified and retains byte offsets into its source. Its q=0 / active=true metadata is an explicit adapter annotation, not a claim to have executed every embedded equation or instruction.

The continuity adapter extends the actual Keddeh LogicalVFS. It preserves logical identity when backing bytes are missing, reports REHYDRATABLE, and accepts restoration only against the retained digest/version. Corrupt bytes and metadata remain rejected. Database failures propagate rather than becoming simulated success. Existing compare-and-set write semantics reject concurrent version conflicts.

## Run

This standalone archive vendors the exact existing LogicalVFS and envelope modules with custody hashes. Python 3.12+ is sufficient for these tools; no downloaded dependencies are required.

`python server.py` launches http://127.0.0.1:3160. It creates a disposable copy of the packaged materialisation; remove/restore controls never change the packaged source. Read full state, inspect identity/digest/receipt, remove the copied carrier, observe REHYDRATABLE and restore verified bytes. Restart resets the exercise copy. Session observations are explicitly session-only, not a fabricated permanent audit. Original durable source history remains in the VFS journal. A per-session token protects mutation requests; this loopback tool is not a public authenticated hosting service.

`python -m unittest discover -v` runs 12 meaningful tests.

`python ingest_state.py owner-state-vfs /path/to/source.txt kex/owner/new-state` ingests another source exactly and journals its separately identified projection. The provided console shows the two supplied source identities; CLI handles additional identities.

`python benchmark.py /path/to/source.txt` measures matched full-payload POSIX and VFS reads, including SHA256 for both and journal validation for VFS. Warm, local measurements cannot establish cold boot, physical energy, remote failover or universal complexity.

## Executed observations

Both supplied source-state carriers were retained byte-for-byte, relocated with logical identities and receipts unchanged, then recovered after actual backing-file removal. Twelve tests cover zero-valued records, empty bytes, carrier loss across adapter restart, bad recovery bytes, corruption, metadata tamper, version mismatch, eight concurrent writers (one commit/seven conflicts), invalid identities and database failure. Browser controls exercise actual API/VFS transitions, source readback, token rejection, mobile layout and reduced motion.

benchmark-results.json records the actual run. The VFS path performs additional journal checks and is slower in this matched payload-read workload. Earlier source-reported 54.97x dictionary-resolution comparisons are different workloads and were not silently reused as this run's result.

## Boundaries

Logical-state preservation is distinct from physical bytes, current process memory and running threads. The software cannot reconstruct lost source bytes from an address alone; verified restoration needs a retained carrier. Source-reported RTL, 70,152 assertion instances, mathematical proofs and distributed performance receipts remain part of the supplied source state; their historical executions are not silently relabelled as newly reproduced here. No replacement algebra or reconstructed RTL was used to test the author's original system.

The named formal-publishing skill was applied for metadata/evidence controls, but its referenced official DOCX template and publishing-standard resource were inaccessible; exact-template conformity is not claimed. No independent review, physical hardware trap suppression, quantum advantage, immutable attacker-proof ledger, remote recovery, zero token costs or measured rack savings is inferred.
