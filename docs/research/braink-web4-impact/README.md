# BRAINK/KEX verified engineering assessment 1.0

Completed source assessment, corrective implementation and local verification. No production deployment, physical energy measurement, firmware secure boot or independent certification is claimed.

Open BRAINK-impact-lab.html for the accessible interactive economics/energy calculator; BRAINK-Web4-assessment.html and PDF contain the complete assessment and boundaries. DOCX is an editable companion; canonical PDF pages are browser-rendered and inspected, not a claim of native Word pagination or unavailable official-template conformance.

KEX_FORWARD_REHYDRATION_RUNTIME_FIXED.html repairs two original JavaScript syntax failures and replaces unsupported authenticated-boot labels with observed descriptor-loading states. This runtime generates address descriptors; it does not implement arbitrary backing storage.

Run `python -m unittest test_energy_model.py` for the four model tests. All sample inputs are scenarios, not power readings. Negative outcomes are preserved.

Install `pip install -r implementation/requirements.txt`, then run `python -m unittest discover -s implementation -v` for ten signed-manifest tests. signed_boot.py provides owner-pinned Ed25519 full-file verification, rejection of altered/extra/missing files, anti-rollback version checks, atomic software activation records and append-only chained observation records. It is a reusable Python module, not a hardware trust root, FROST implementation or autonomous OS executor. Protect keys and state and reverify immutable slot content immediately before execution. An attacker able to rewrite the entire ledger can rebuild its chain unless an external trusted anchor exists.

The existing namespace runtime passed 90 tests in an isolated environment with declared dependencies. See verification-summary.json and existing-runtime-tests.log. Browser verification evidence covers the corrected carrier and desktop/mobile/reduced-motion impact lab. No power meter was available.

The original pasted verifier audit is reproducible using `python reproduce_boot_audit.py /path/to/Pasted\ text.txt`; it excludes disk-formatting and UI startup. Original private transcript and giant embedded runtime are not redistributed. Custody hashes identify inspected originals. Component benchmarks in the supplied original paper remain source-reported because their harness was unavailable.

Rights reserved pending owner designation. Upstream sources retain their own licences. Publishing-template conformance, independent assessment, actual rack/client energy qualification and authenticated production deployment remain explicitly unresolved.
