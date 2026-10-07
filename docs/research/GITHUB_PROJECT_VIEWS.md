# GitHub programme planning

The programme has a master issue (#27), ten batch issues (#17–#26), a versioned
100-step ledger, acceptance evidence and release milestones. The first twenty
steps are verified. Batch 03 is active; later batches remain queued behind their
dependencies. Critical runtime continuity fixes take priority in batches 03–04.

Apply the repeatable issue configuration with:

```sh
python scripts/planning/apply_github_plan.py
```

This uses the existing GitHub authentication, assigns the programme to Keddeh1,
and applies status and priority labels. It does not close unverified work or
execute runtime changes. Existing batch milestones and evidence labels remain.

## Native Project access

On 2026-10-07, `gh project list --owner Keddeh1 --format json` returned no
visible projects. Creating **KEDDEH Enterprise Engineering Programme** failed
with GraphQL `Resource not accessible by integration (createProjectV2)`.
This is an API permission denial, not a missing repository write permission.
No Project, custom fields or native views were created. Issue planning remains
usable and applied independently of that denial.

## Project configuration to apply when the API permits it

Repository association: all nine owner-runtime family repositories. Add the
master issue and batch issues, then family delivery and failure issues by URL.
Use GitHub's native Status field with Backlog, Ready, In progress, Blocked,
In review and Done. Add Priority (Critical, High, Normal), Batch (number),
Evidence URL (text), Repository (text) and Gate (Research, Implementation,
Qualification, Promotion). Done requires the documented acceptance evidence.

| View | Layout | Filter/grouping | Purpose |
|---|---|---|---|
| Delivery | Board | Programme label; group by Status | Current execution and dependency handoffs |
| Failures | Table | Critical priority or blocked status | Root cause, recurrence controls and acceptance evidence |
| Qualification | Table | Evidence-required label; group by milestone | Review executed checks before promotion |
| Repository families | Table | Group by Repository | Package version, subscriptions and deployment readbacks |
| Roadmap | Roadmap | Milestone and batch order | Sequence the 100 steps without inventing delivery dates |

Current labels and milestone assignments can be read directly from GitHub.
The table specifies intended native views; it is not evidence of active views.

**Next task: step 21 — trace bilateral intent persistence and actor acknowledgement crash boundaries.**
