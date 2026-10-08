# BRAINK/KEX Web4 impact assessment candidate

Research branch; no production deployment, security certification, energy measurement or independent approval is claimed.

Read BRAINK-Web4-assessment.html, claim-register.json, sources.json and runtime-custody.json. The report evaluates technical architecture, market comparators, professional use cases, economic costs, environmental boundaries and a qualification protocol. The optional rendered PDF is supplied in the downloadable delivery archive.

Run `python3 -m unittest test_energy_model.py` and `python3 energy_model.py scenario-input.json`. All scenario inputs are assumptions; change them to measured and sourced values before making a customer savings claim. The model retains negative outcomes, separates net energy and operational carbon, and does not invent embodied-carbon credits.

The supplied illustrative boot-code audit can be reproduced with `python3 reproduce_boot_audit.py '/path/to/Pasted text.txt'`. It extracts only hash/verifier functions, redirects their paths to temporary directories, and excludes runtime UI startup and destructive disk provisioning. Python executes only that narrowly selected supplied code; review the source input before using another document. The original pasted text is not redistributed. Its SHA-256 and specific findings are in boot-audit.json. The findings do not establish defects in unrelated original BRAINK compilers or code.

The original v74 benchmark and complete compiler proof/corpus were not available for verification. Existing original runtime source custody and prior session evidence remain separate from this new research. The mandatory Keddeh publishing template was unavailable; layout compliance is pending. Rights remain reserved pending owner designation, with upstream sources retaining their own attribution and terms.
