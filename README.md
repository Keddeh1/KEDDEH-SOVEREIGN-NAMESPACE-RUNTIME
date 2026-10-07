# KEDDEH Sovereign Namespace Runtime

Repository foundation for REV-002: an evidence-gated namespace runtime with preserved DNS custody, independent authoritative nodes, exact-source service admission, immutable generations, and independent assessment.

Track A routes apex/www traffic through the existing Squarespace authority. Track B builds ns1/ns2 and later changes registrar delegation. Neither transaction establishes completion of the other.

## Development

Python 3.12+ with checksum-pinned cryptography/dnspython dependencies. No live credentials are required for the local tests.

```sh
python -m venv .venv
source .venv/bin/activate
UV_CACHE_DIR=/workspace/.cache/uv uv sync --frozen --python python
python -m unittest discover -s tests -v
python -m keddeh_namespace.evidence evidence.example.json
```

The example ledger deliberately fails promotion. The validator checks the structure and consistency of submitted evidence; it does not authenticate signatures, execute checks, or independently prove deployment.

## Status

The local runtime now implements signed observations/assessments, durable generation registry, content-addressed VFS, safe archive admission/replay, bounded topology policy, deterministic zone/config staging and fail-closed preflight. Production gates remain incomplete. No DNS records, delegation, servers, storage allocations, or application deployments have been changed. The original document's 33/33 tests, 16 MCP tools, registrations, and existing implementation claims are supplied assertions, not independently verified facts.

See [the preserved source](docs/REV-002-source.txt), [architecture](docs/ARCHITECTURE.md), [implementation plan](docs/IMPLEMENTATION_PLAN.md), and [cutover runbook](docs/A1_SQUARESPACE_CUTOVER.md). Example configuration contains unset public IPs and preservation hash intentionally; production must reject it until measured inputs are available.

## Exact-source custody

`source-manifest.json` preserves all four owner-supplied archive sizes and hashes. Verify a locally supplied archive without extraction or execution:

```sh
python -m keddeh_namespace.source_custody source-manifest.json braink-2.1-full /path/to/archive
```

A match proves the bytes read match the expected digest; it does not prove safe extraction, trusted authorship, running services, or deployment. Actual source archives remain unavailable. Use operator-controlled local files for this foundation checker; hardened staging and write-once extraction remain pending.

## Related uploaded sources

See [component mapping](docs/COMPONENT_MAP.md) and [custody inventory](docs/UPLOAD_INVENTORY.json) for the eight additional uploads. These sources were mapped statically; the workstation archive was also separately admitted and build-tested. Its frontend build is blocked by corrupted source. No uploaded application runtime was integrated.

## Observation envelope and native labels

`keddeh_namespace.envelope` provides strict v1 observations, deterministic project JSON encoding, domain-separated state/phase roots, and complete-chain verification against an externally retained head digest. It rejects unknown fields, ambiguous floating-point payloads, missing identities and noncanonical timestamps. It is not a signature verifier or an immutable storage engine.

`keddeh_namespace.native_labels` implements the PDF's occupied labels (...,-3,-2,1,2,3,...) through an explicit displacement adapter; native 0/-1 are invalid while measurement displacement 0 maps to native origin 1. DNS/storage protocol integers retain their ordinary meanings. See [the envelope contract](docs/ENVELOPE_CONTRACT.md).

## Delivery tracking

Use the [GitHub workflow](docs/GITHUB_WORKFLOW.md) for milestones, issue dependencies, labels and active filtered issue lists. Project creation is currently denied by the integration; its field/view configuration is recorded separately as pending.

## Runtime implementation and evidence

See [runtime operations](docs/RUNTIME_OPERATIONS.md) and [validation summary](docs/evidence/validation-summary.json). Run the optional Docker authority test with `.venv/bin/python scripts/test_knot_integration.py`. Local passing tests do not establish production DNS delegation or storage capacity.

## Enterprise governance

[Controlled governance baseline](governance/README.md): document lifecycle, accountability, change/release gates, assurance, access/source custody and incident/recovery standards. Validate with `python scripts/check_governance.py`. GitHub review routing and automated integrity checks are defined; independent review and platform branch-rule enforcement remain separately tracked.

## WEB4 architecture and cloud launch — 0.2.0

The uploaded launch packages now run as actual cloud-workspace processes: ten KEX workstation nodes, estate/network MCP, R36 HTTP/Python workers, owner broker and outbound host agent. Original terminal, HTML carrier and resident research UI connect through an authenticated cloud panel. Propagation can explicitly actuate R36 registers and retain signed namespace readbacks.

Start with `bash scripts/start_web4_cloud.sh`; inspect with `.venv/bin/python -m keddeh_namespace.web4_runtime status`. See [the controlled launch runbook](governance/WEB4_CLOUD_RUNTIME_RUNBOOK.md) and [live integration evidence](docs/evidence/web4-integration.json). Owner originals stay in the private library; the launcher pins their identities and records its derivations.
