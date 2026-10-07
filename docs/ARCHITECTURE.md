# Architecture inferred from REV-002

## Transactions and custody

Track A changes only current hosted web records after complete zone inventory. Mail, verification, CAA and unrelated records remain under custody. Track B imports that inventory into two independently operated authoritative nodes, then promotes delegation only after direct predelegation checks. Stable public IPs, glue and DNSSEC DS coordination are external prerequisites.

## State and lineage

Exact source bytes enter content-addressed, write-once paths. Desired state becomes a signed immutable generation. Nodes read back the generation; services prove identity and health; the archive proves replay and restore. Backward traversal must recover source/configuration and the author/verifier ledger from live runtime identity. stateRoot and phaseRoot have distinct roles and remain separately represented.

Each node requires an observed 10 TB logical VFS; the archive requires an observed 100 TB plane. A configured number is not capacity evidence. Logical addressing alone does not prove available physical storage or durability.

## Genesis topology

Root services remain genesis participants. Each launches exactly three child domains, and each child supplies two independent return connections. Identity, signed envelopes, bounded leases, replay protection, resource ceilings and cooldowns are required controls. The reference 0.297 does not establish a measured health threshold.

## Trust boundary

Generators cannot verify their own promotion. Atomic receipts must bind runtime identity, source hash, command/transaction, readback, lineage and independent assessment. The initial local validator enforces required evidence fields and separate assessor identity; cryptographic trust and live execution remain future implementation work.
