# KEDDEH Sovereign Namespace Runtime

Repository foundation for REV-002: an evidence-gated namespace runtime with preserved DNS custody, independent authoritative nodes, exact-source service admission, immutable generations, and independent assessment.

Track A routes apex/www traffic through the existing Squarespace authority. Track B builds ns1/ns2 and later changes registrar delegation. Neither transaction establishes completion of the other.

## Development

Python 3.12+, no external dependencies or live credentials required for the current foundation.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
python -m keddeh_namespace.evidence evidence.example.json
```

The example ledger deliberately fails promotion. The validator checks the structure and consistency of submitted evidence; it does not authenticate signatures, execute checks, or independently prove deployment.

## Status

Repository scaffolding, the ledger validator, and exact archive byte verification are implemented. No DNS records, delegation, servers, storage allocations, or application deployments have been changed. The original document's 33/33 tests, 16 MCP tools, registrations, and existing implementation claims are supplied assertions, not independently verified facts.

See [the preserved source](docs/REV-002-source.txt), [architecture](docs/ARCHITECTURE.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md), and [cutover runbook](docs/A1_SQUARESPACE_CUTOVER.md). Example configuration contains unset public IPs and preservation hash intentionally; production must reject it until measured inputs are available.

## Exact-source custody

`source-manifest.json` preserves all four owner-supplied archive sizes and hashes. Verify a locally supplied archive without extraction or execution:

```sh
python -m keddeh_namespace.source_custody source-manifest.json braink-2.1-full /path/to/archive
```

A match proves the bytes read match the expected digest; it does not prove safe extraction, trusted authorship, running services, or deployment. Actual source archives remain unavailable. Use operator-controlled local files for this foundation checker; hardened staging and write-once extraction remain pending.

## Related uploaded sources

See [component mapping](docs/COMPONENT_MAP.md) and [custody inventory](docs/UPLOAD_INVENTORY.json) for the eight additional uploads. These are statically assessed references; no uploaded implementation has been integrated or executed.
