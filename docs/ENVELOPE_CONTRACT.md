# Observation envelope v1

Schema: keddeh.observation.v1. Exact required fields: schema, runtime_id, source_sha256, generator_id, observer_id, metric, execution_plane, observed_at, transaction, readback, stateRoot, phaseRoot, parent_envelope_sha256. Unknown fields require a version change. observed_at uses UTC YYYY-MM-DDTHH:MM:SS.ffffffZ.

Parent is null only at genesis. Later observations reference the canonical digest of the immediately preceding envelope. verify_chain requires complete history from genesis and an externally retained trusted head. Truncation and changed genesis are rejected relative to that head. Obtaining the head from the same untrusted source as the chain provides no independent trust.

Project encoding uses sorted string keys, compact UTF-8 JSON, no floats, and exact JSON scalar/list/object types. It is not RFC 8785 JCS. A future language implementation must reproduce this encoding with fixed test vectors; do not substitute a different JSON serializer silently. Hash input excludes no fields, and envelope digest is kept outside the envelope to avoid self-reference.

State and phase roots use keddeh.root.v1 envelopes with separate kind domains. Same payload therefore produces different roots. Callers still need explicit content schemas to define what belongs to state versus synchronization phase.

Observer and generator can coincide for local observations. This is not independent assessment. Production promotion still requires a distinct verifier, trusted signature validation, durable immutable receipts, actual command/readback evidence and the complete acceptance ledger. Existing evidence.py remains a separate structural promotion checklist; it is not automatically satisfied by a valid observation chain.

The native label adapter implements rho(1)=0, rho(n)=n-1 for n>=2, rho(-n)=-(n-1) for n>=2. Native addition is rho inverse of summed displacements. This representation is isolated from standard network and operating-system interfaces.
