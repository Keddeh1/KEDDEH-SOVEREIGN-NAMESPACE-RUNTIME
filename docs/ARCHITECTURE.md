# KEDDEH owner-runtime architecture

The current executable architecture combines supplied KEX HTML runtimes, an R36
multiplexer, owner software control models, recursive dual-homed network domains,
content-addressed VFS and one persistent controller per repository family. Release
0.3.2 runs on the current Docker host in nine families. The initial REV-002
namespace, two-node authority and large-capacity objectives remain separate
promotion requirements; they are not established by this same-host deployment.

Start with the [full architecture specification](architecture/SYSTEM_ARCHITECTURE.md),
[technology and trajectory assessment](architecture/TECHNOLOGY_ASSESSMENT.md),
[data and attribution contract](architecture/DATA_AND_ATTRIBUTION.md), and
[standardization audit](architecture/STANDARDIZATION_AUDIT.md).

The controlled baseline is [ARC-001](../governance/ARCHITECTURE_AND_ATTRIBUTION_STANDARD.md).
Its document hash and lifecycle are in `governance/document-register.json`.
Operational contracts cover every exposed action, process and configuration group
in [the package index](package/README.md); the source inventory lists 149 Python
functions/methods. These documents describe behavior and evidence, not an
independent certification or worldwide novelty finding.
