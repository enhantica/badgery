# badgery roadmap — milestones & tasks

Milestone prefix **B** (registered in the org portfolio —
`enhantica/org` `knowledge/roadmap/portfolio.md`). Tier **C (solo)** under the org
orchestration model: one agent per task, PR-gated, `feature → main` squash (ORG-0003).
Status: ✅ done · 🟡 partial · ⬜ open. `AUD-##` = findings in the org audit
(`enhantica/org` `audit/ISSUES.md`); resolve per ORG-0025 (the fixing PR flips the finding's
status there in the same change).

## B01 — Gitflow funeral & release realignment — audit R4, AUD-05

badgery still carries the pre-org gitflow machinery ORG-0003 deleted; this milestone removes
every artifact of it in one sweep.

| Task | Status | What |
|---|:--:|---|
| B01-T01 | ⬜ | **Delete the live remote `develop` branch** and its "develop branch protection" ruleset; prune stale merged branches (`audit`, `codecov-flags`, `more-lint-fixes`, `py314`, …) and their orphaned dashboard output dirs (AUD-05/14) |
| B01-T02 | ⬜ | **Remove `backmerge-pr.yml` and `release-pr.yml`**; realign the release flow to ORG-0004 (drafterino draft on `main` pushes → owner publishes → tag-driven post-release) (AUD-05) |
| B01-T03 | ⬜ | **Workflow hygiene**: top-level `permissions:` for `dashboard.yml`/`quality.yml`/`security.yaml` (AUD-09); pin `github/ossar-action@main` → release/SHA (AUD-06); SHA-pin the rest (AUD-07, ORG-0024); keep the main ruleset, add required checks when ORG-T06 ships |

## B02 — Org-base compliance — ORG-T29

| Task | Status | What |
|---|:--:|---|
| B02-T01 | ⬜ | **Audit-layout migration**: root `AUDIT_ISSUES.md`/`AUDIT_RECOMMENDATIONS.md` → `audit/{README,ISSUES,RECOMMENDATIONS}.md` (ORG-0025; org ORG-T25) |
| B02-T02 | ⬜ | **ORG-0014 alignment**: add mypy (strict, exclude-only-shrinks) alongside the existing ruff/interrogate/docformatter; drop the `[activation.env]` PYTHONPATH hack in favor of a proper editable install (AUD-21) |
| B02-T03 | ⬜ | **License**: execute the owner's AUD-04 decision (relicense MIT→BSD-3 or keep MIT under an ORG-0020 amendment); then SPDX headers (ORG-0016) |
| B02-T04 | ⬜ | **Labels + health defaults**: full label set via `.github` sync (AUD-11); inherit community-health defaults at ORG-T22 |
| B02-T05 | ⬜ | **Formatting**: keep prettier+nodejs only until kempt's K01-T07 pilot replaces the `nonpy-format-*` tasks (AUD-13) — no further investment in the interim stack |
