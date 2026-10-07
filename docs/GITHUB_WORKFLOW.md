# GitHub delivery workflow

## Live repository tracking

The repository has four evidence-based milestones and 13 implementation/operations issues. No deadlines are invented; set target dates only after resources and change windows are agreed. Track A remains independent of Track B. Native blocked-by links express execution prerequisites; milestone numbers are not a requirement to serialize independent tracks.

Labels carry parallel dimensions: track, area, type, priority, external blocker and evidence requirement. Use one track, one type, one priority, relevant areas and applicable blocker labels. Keep GitHub issue state for open/closed and Project Status for workflow state; do not add duplicate status labels. Existing standard GitHub labels are retained.

| Milestone | Scope | Issues |
|---|---|---|
| M1 | Current-authority custody and web cutover | #1–#2 |
| M2 | Trusted receipt/storage/registry/source foundation | #3–#6 |
| M3 | Independent runtime, replay, services, topology and operator integration | #7–#11, #13 |
| M4 | Independent assessment and registrar delegation | #12 |

Start independent local development with #3 signed receipts and #4 VFS while obtaining the current-zone custody inputs for #1 and exact service sources for #6. #13 is P2 follow-on operator work. External blockers are named in issues; local implementation can still proceed where inputs are not needed.

## Completion and review

Link implementation PRs to issues. Use closing keywords only when every issue acceptance check is satisfied. A merged partial implementation does not close a production-validation issue. Record executed commands, exit status, readback and source/runtime/generation references; keep secret material outside issues and Git. Independent promotion assessment must remain separate from generator identity. Require operation-specific authorization before actual DNS/registrar transactions.

## Project and view configuration

GitHub denied createProjectV2 with Resource not accessible by integration. No Project or saved Project views were created. This permission is separate from repository code/issues access. The machine-readable desired configuration is docs/GITHUB_ROADMAP.json; fields and views below are prepared, not active.

Desired Project: **KEDDEH Namespace Runtime — REV-002**, owned by Keddeh1 and linked to this repository. Add all 13 tracked issues and repository-scoped auto-add for later issues/PRs. Keep the Project private unless the owner explicitly chooses otherwise; the repository itself is public.

Fields: Status = Backlog, Ready, In progress, In review, Blocked, Done; Evidence = Pending, Executed, Independently verified. Use built-in Milestone, Labels, Assignees and Linked pull requests instead of duplicating them. Set Ready only when dependencies and required inputs allow work. Set Done only after issue acceptance is met and the issue is closed. Do not claim completed code is independently verified merely because unit tests pass.

| Prepared view | Layout | Filter | Group |
|---|---|---|---|
| Delivery board | Board | repository, open items | Status |
| Track A — Web cutover | Table | label:track:a-web | Milestone |
| Track B — Runtime | Board | label:track:b-runtime, open items | Status |
| External blockers | Table | label:blocked:external, open items | Milestone |
| Acceptance evidence | Table | label:evidence:required | Evidence |
| Milestone roadmap | Table | repository | Milestone |

For the roadmap, use milestone grouping until real dates exist. A dated roadmap layout should be enabled only after measured schedules exist. Initial issues have Pending evidence. Items with external blockers start Blocked; dependency-free local implementation issues start Ready; remaining items start Backlog.

## Active issue views available now

- [All implementation work](https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/issues?q=is%3Aissue%20is%3Aopen)
- [Track A](https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/issues?q=is%3Aissue%20is%3Aopen%20label%3Atrack%3Aa-web)
- [Track B](https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/issues?q=is%3Aissue%20is%3Aopen%20label%3Atrack%3Ab-runtime)
- [External blockers](https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/issues?q=is%3Aissue%20is%3Aopen%20label%3Ablocked%3Aexternal)
- [P0 prerequisites](https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/issues?q=is%3Aissue%20is%3Aopen%20label%3Apriority%3Ap0)
- [Acceptance checklist](https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/issues?q=is%3Aissue%20label%3Aevidence%3Arequired)

These are filtered issue lists, not saved Project views. Milestones: https://github.com/Keddeh1/KEDDEH-SOVEREIGN-NAMESPACE-RUNTIME/milestones
