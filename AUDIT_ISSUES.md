# Badgery — project audit: issues

- **Date:** 2026-07-06
- **Branch audited:** `main` (commit `6ffe58f`), recorded on branch `audit`
- **Scope:** all tracked files — source (`src/badgery/`), tests, CI workflows,
  packaging/tooling config, docs
- **Method:** full manual read of every tracked file, local execution of the
  quality gates (`pixi run tests` → 61/61 pass, `tests-cov` → 85.4%,
  `py-lint-check` / `py-format-check` → clean, `docstring-cov` → 85.6%), plus
  targeted repro scripts and a PyPI registry check. No helper agents.

Issue counts: **2 highest, 7 high, 10 medium, 11 low, 8 lowest** (38 total).

---

## Highest

### H1. Codecov token hardcoded in two places in the source code

- **Where:** `src/badgery/badges.py:84` and `src/badgery/render.py:265`
- **What:** `os.environ.get('CODECOV_TOKEN', 'qtsB5Q5BXO')` — a real token is
  committed to the repository and duplicated in two modules. It is used as the
  fallback whenever the `CODECOV_TOKEN` env var is unset, i.e. for every local
  run and for every third-party user of the package.
- **Impact:** A credential lives permanently in git history and in any built
  wheel. It appears to be the Codecov _graphing_ token of a different project
  (`easyscience/diffraction-lib`, see M8), so every badgery user silently sends
  that token to codecov.io in query strings for unrelated repositories. Even if
  graphing tokens are low-privilege, committing any token is a bad precedent and
  the token can be revoked at any time, silently breaking the fallback path.
- **Fix:** Remove the literal from both call sites (default to `''`/`None` and
  skip the `token` query parameter when absent). Revoke the exposed token in
  Codecov. Deduplicate the URL-building logic so it exists in one place only
  (today `render._codecov_percent` re-implements `badges.codecov_badge_img`).

### H2. README instructs `pip install badgery`, but the package does not exist on PyPI

- **Where:** `README.md:22` (`pip install -U badgery`); confirmed
  `https://pypi.org/pypi/badgery/json` returns **404**.
- **What:** The documented installation path is broken; the project name is
  unregistered on PyPI.
- **Impact:** Every new user's first step fails. Worse, because the README
  publicly instructs people to `pip install badgery`, anyone could register the
  name on PyPI and have users install attacker-controlled code (name-squatting /
  supply-chain exposure).
- **Fix:** Register and publish the package (see recommendations: a
  `publish-pypi.yaml` workflow using PyPI Trusted Publishing) — or, until then,
  change the README to the actually working
  `pip install git+https://github.com/enhantica/badgery`.

---

## High

### H3. Hand-rolled YAML parser silently mis-parses inline comments — disabled cards stay enabled

- **Where:** `src/badgery/config.py:27-45` (`_parse_scalar`), `config.py:60-103`
  (`load_cards_from_yaml`), `config.py:106-153` (`load_settings_from_yaml`)
- **What:** The parser never strips inline `# comments`. Verified repro:
  `enabled: false # temporarily disabled` parses to the _string_
  `'false # temporarily disabled'`, which is truthy, so the card stays
  **enabled**. Likewise `report: path.json # note` yields a corrupted path and
  the report is silently not found. Numbers are also never parsed (any numeric
  value stays a string), nested structures are unsupported, and unknown syntax
  is silently dropped rather than rejected.
- **Impact:** A file named `.badgery.yaml` promises YAML semantics but the
  parser diverges from them in silent, behavior-changing ways. Users who add a
  perfectly valid comment get the opposite of what they configured, with no
  warning. No test covers this (checked `tests/unit/badgery/config/`).
- **Fix:** Strip inline comments and parse ints/floats in `_parse_scalar` at
  minimum; better, replace the hand parser entirely (see recommendations —
  stdlib `tomllib` keeps the zero-dependency goal, or PyYAML as a dependency).

### H4. `GithubWorkflowMetric.badge()` calls a method that does not exist — `refs()`/`badge()` API is broken

- **Where:** `src/badgery/_metrics/workflow.py:47`
  (`self.badge_gen.github_badge(...)`) — `BadgeGenerator`
  (`src/badgery/badges.py`) has no `github_badge` method; also
  `src/badgery/_metrics/base.py:76-89` (`BaseMetric.refs()` calls
  `self.badge(...)`, which raises `NotImplementedError` for `CodecovMetric`,
  `LinesOfCodeMetric` and the count metrics).
- **What:** `GithubWorkflowMetric.refs()` triggers `AttributeError` on first
  use; `BaseMetric.refs()` raises for several subclasses. Nothing in the current
  render path calls `refs()` (verified by grep — zero call sites), so this is a
  dead-but-crashing public API surface.
- **Impact:** Latent crash for any consumer of the documented-looking
  `refs()`/`badge()` API; dead code inflates the maintenance surface and the
  coverage denominator.
- **Fix:** Delete the `badge()`/`refs()` chain and the empty badge helpers in
  `BadgeGenerator` (see L2), or implement them properly and add tests.

### H5. Coverage workflow never uploads to Codecov, though its job claims to — the Codecov card can never work

- **Where:** `.github/workflows/coverage.yaml:52-71` (job `unit-tests-coverage`,
  comment says "upload to Codecov"); `.badgery.yaml:46-49` (codecov card,
  `flag: unittests`)
- **What:** The job generates `coverage-unit.xml` and ends. There is no
  `codecov/codecov-action` (or equivalent) step, no `CODECOV_TOKEN` secret use,
  and no `unittests` flag upload anywhere in CI.
- **Impact:** Codecov never receives data for this repo, so the dashboard's
  "Unit test coverage (Codecov)" card is permanently "unknown", and the
  `CI_CODECOV_*` env fallbacks are never populated either. CI minutes are spent
  producing an XML file that is thrown away.
- **Fix:** Add a `codecov/codecov-action@v5` step with
  `files: coverage-unit.xml`, `flags: unittests` (matching the card), and the
  repo's own upload token / OIDC.

### H6. Scheduled cleanup workflow passes empty inputs — risks deleting far more workflow history than intended

- **Where:** `.github/workflows/cleanup.yaml:72-80`
- **What:** On the monthly `schedule` trigger, `github.event.inputs.*` are all
  empty strings, and empty strings are what get passed to
  `Mattraks/delete-workflow-runs` for `retain_days` and `keep_minimum_runs`. An
  explicitly supplied empty input bypasses the action's own defaults; the
  action's number coercion of `''` is 0 (or NaN, depending on version).
- **Impact:** The monthly run may execute with retain-0/keep-0 semantics — i.e.
  delete **all** workflow run history — or fail outright. Either way the
  behavior is undefined and it is a destructive, unattended job.
- **Fix:** Provide explicit fallbacks:
  `retain_days: ${{ github.event.inputs.days || 30 }}` and
  `keep_minimum_runs: ${{ github.event.inputs.minimum_runs || 6 }}` (same
  pattern for the other inputs), and set `dry_run` once to verify.

### H7. Generated dashboard HTML embeds unescaped strings — stored XSS in the published page

- **Where:** `src/badgery/render.py:599-653` (`_value_item_html`, `_card_html` —
  `branch_label`, `title`, `text` interpolated raw), `render.py:683-713`
  (`render()`)
- **What:** Card titles (config), branch names (CLI `--branch`, CI
  `github.head_ref`), and status text are inserted into HTML without
  `html.escape()`.
- **Impact:** The dashboard is published to GitHub Pages by `dashboard.yaml` for
  **every pushed branch**. A branch named e.g. `<img src=x onerror=alert(1)>`
  (branch names allow `<`, `=`, spaces are the only real limitation) results in
  stored XSS on the org's `github.io` domain. Anyone who can push a branch (or
  get a PR branch built) can inject.
- **Fix:** `html.escape()` every interpolated value in the renderer; add a
  regression test rendering a hostile branch name/title.

### H8. Claimed Python/OS support is not tested: CI runs only Ubuntu + Python 3.13

- **Where:** `pyproject.toml:17-24` (classifiers 3.11-3.14, "OS Independent");
  `pixi.toml:30-31,48-49` (only a `py313` feature);
  `.github/workflows/test.yaml:36-41,92-97` (matrix contains only
  `ubuntu-latest`); commit `a97abef` ("Add Python 3.14 support") changed
  **metadata only**.
- **What:** Every CI job — source tests, wheel tests, coverage — runs on one OS
  and one interpreter (3.13). The 3.11/3.12/3.14 and Windows/macOS claims have
  never been exercised.
- **Impact:** Support claims in package metadata are unverified; regressions on
  other interpreters/OSes (e.g. path/encoding issues on Windows — the tool
  writes files and shells out in CI recipes) would ship unnoticed.
- **Fix:** Add pixi features/environments for 3.11-3.14 and extend the test
  matrix across `{ubuntu, macos, windows} × {3.11 … 3.14}` (the matrix
  scaffolding already exists).

### H9. Dashboard config references workflows that do not exist — cards are permanently "unknown"

- **Where:** `.badgery.yaml:11-14` (`file: test-pypi.yaml`) and
  `.badgery.yaml:64-67` (`workflow: publish-pypi.yaml`) — neither file exists in
  `.github/workflows/` (also referenced by comments in `test.yaml:9` and
  `quality.yaml:9`); related: `security.yaml` only triggers on
  `pull_request`/manual, so its per-branch badge has no data for most branches
  (`.badgery.yaml:58-61`).
- **What:** The repo's own dashboard requests status badges for `test-pypi.yaml`
  and `publish-pypi.yaml`, which GitHub 404s.
- **Impact:** Two cards (plus, most of the time, the security card) render
  "unknown" forever — on the project's own showcase dashboard. It also documents
  a release pipeline that is not actually there (ties into H2).
- **Fix:** Add the missing `test-pypi.yaml`/`publish-pypi.yaml` workflows (the
  release process needs them anyway), or remove/disable those cards; align
  `security.yaml` triggers (run on push to main/develop too) so the badge has
  per-branch data.

---

## Medium

### M1. Third-party GitHub Action pinned to a moving branch; no SHA pinning anywhere

- **Where:** `.github/workflows/security.yaml:33` (`github/ossar-action@main`);
  all other workflows pin by mutable tags (`@v5`, `@v0.9.0`, `@v2`, `@v3`,
  `@v7`).
- **What:** `@main` means every run executes whatever is currently on that
  branch; tags are also mutable. OSSAR itself is effectively dormant upstream.
- **Impact:** Classic supply-chain exposure: a compromised or careless upstream
  change executes with repo credentials — in `dashboard.yaml` that includes
  `GH_API_PERSONAL_ACCESS_TOKEN` (a cross-repo PAT).
- **Fix:** Pin all actions to full commit SHAs (with a version comment), let
  Dependabot bump them (see M10); replace OSSAR with CodeQL (maintained,
  first-party).

### M2. Workflow token permissions are not least-privilege

- **Where:** `.github/workflows/security.yaml` (no `permissions:` block at all —
  SARIF upload needs `security-events: write`, so it currently relies on the
  repo's default token setting and fails if defaults are read-only);
  `quality.yaml`, `coverage.yaml` (jobs), `dashboard.yaml`, `release-notes.yaml`
  inherit defaults instead of declaring minimal `permissions`.
- **Impact:** Either broken (security scan upload) or over-privileged runs,
  depending on org/repo default token configuration.
- **Fix:** Declare explicit minimal `permissions:` in every workflow
  (`contents: read` baseline; `security-events: write` for the SARIF upload).

### M3. Renderer does sequential live HTTP fetches per card and branch, scraping badge SVGs

- **Where:** `src/badgery/render.py:191-222` (`_fetch`, 8 s timeout),
  `render.py:224-297` (`_github_badge_status`, `_codecov_percent`,
  `_codefactor_grade`), called from `_status_*` for each of 3 branch rows per
  service card
- **What:** With the repo's own config (4 workflow cards + codecov +
  codefactor), a render performs up to 18 sequential HTTPS requests; each dead
  endpoint costs up to 8 s (~2.4 min worst case). Results are not cached, so
  identical URLs may be fetched repeatedly. Status is extracted by regexing the
  SVG internals of GitHub/Codecov/CodeFactor badges — an undocumented, unstable
  interface (a markup change silently turns everything "unknown", cf. the fixed
  word-list in `_github_badge_status:240`).
- **Impact:** Slow, fragile renders; silent degradation when providers change
  badge markup.
- **Fix:** Fetch concurrently (`ThreadPoolExecutor`) and memoize per-URL; prefer
  stable APIs: GitHub REST (`actions/runs?branch=...&status=`) with
  `GITHUB_TOKEN`, Codecov API v2 — keep badge scraping only as fallback.

### M4. CI runs are heavily duplicated

- **Where:** `test.yaml:3-13` and `quality.yaml:3-15` trigger on **both**
  `push: branches: ['**']` and `pull_request: branches: ['**']` → every PR
  commit runs everything twice; the unit test suite executes three times per
  change (`test-source`, `test-package`, `coverage.yaml`); the dashboard is
  dispatched twice per push (`test.yaml:130-149` and `coverage.yaml:74-93`);
  `release-notes.yaml:27-35` installs the full pixi environment for a job whose
  action likely doesn't need it; no `paths-ignore` anywhere (docs-only changes
  trigger the world).
- **Impact:** Roughly 2-3× the necessary CI minutes and queue latency; noisy
  duplicate status checks on PRs.
- **Fix:** Restrict `push` triggers to `main`/`develop` (+ tags where relevant)
  and let `pull_request` cover feature branches; single dashboard dispatch; drop
  the pixi setup from release-notes if unneeded; add `paths-ignore: ['**.md']`
  where sensible.

### M5. Development environment depends on the project's own remote git state

- **Where:** `pixi.toml:25-26`
  (`badgery = { git = "https://github.com/enhantica/badgery", extras = ["dev"] }`)
  plus the `PYTHONPATH` shadowing hack in `pixi.toml:1-7`; `tests/conftest.py`
  repeats the same hack with `sys.path`.
- **What:** The default environment installs badgery _from GitHub_ (a circular
  self-dependency pinned in `pixi.lock`), then masks that installed copy with
  `src/` via `PYTHONPATH`. In CI, `test.yaml`'s `test-package` job first
  resolves that remote copy before swapping in the locally built wheel.
- **Impact:** Fresh setups require network access to the repo itself; the lock
  file churns with a self-referential revision; the installed entry point can
  silently run _older remote_ code while imports resolve to local `src/` — a
  confusing split-brain; offline development is broken.
- **Fix:** Use an editable local path dependency
  (`badgery = { path = ".", editable = true, extras = ["dev"] }`), then delete
  the `PYTHONPATH` activation hack and the `conftest.py` sys.path shim.

### M6. Legacy "master" naming is wired through the entire codebase

- **Where:** `src/badgery/_metrics/base.py:58-60` (`self.master`),
  `render.py:586-597` (branch key `'master'` → attr mapping), env var scheme
  `CI_*_MASTER` (`codecov.py:30`, `codefactor.py:28`, `workflow.py:41`,
  `cli.py:133-181`), `config.py:114-118` (`default_branch` fallback `'master'` —
  while README/`.badgery.yaml` use `main`), `badges.py:66,87` (badge URL
  special-cases the literal `'master'` only).
- **Impact:** Constant mental translation (`master` == whatever `default_branch`
  is); the `'master'` default contradicts the README example and GitHub's
  default; the URL special-case behaves differently for repos whose default
  branch is literally `master` vs `main`.
- **Fix:** Rename the internal slot/keys to `default`/`develop`/`feature`,
  default `default_branch` to `'main'`, and drop the `'master'` special-case in
  badge URLs (always pass `?branch=`).

### M7. Critical interfaces are undocumented

- **Where:** README vs. code: the entire `CI_*` env-var fallback system
  (`CI_CODECOV_MASTER`, `CI_WORKFLOW_<NAME>_<BRANCH>`, `CI_COMPLEXITY_MASTER`,
  …) — the _only_ way to feed codecov/codefactor values without live fetches —
  appears nowhere in the docs; the full card type list and key aliases
  (`workflow:` vs `file:`, `radon_ff`, `radon_funcs_per_file`) are undocumented;
  the `**`→branch substitution in report paths (`cli.py:49-65`) is undocumented;
  `BADGES_LOG_LEVEL` (`cli.py:114`) is undocumented and oddly named; `--output`
  defaults to `BADGES.html` while all CI usage writes `index.html`.
- **Impact:** Users cannot discover most of the tool's behavior except by
  reading the source; a dashboard tool ships without a single screenshot.
- **Fix:** Add a configuration reference (card types, keys, env vars) and a
  screenshot to the README; align the env-var prefix (`BADGERY_*`).

### M8. Default repository hardcoded to another project

- **Where:** `src/badgery/badges.py:9`
  (`REPO_DEFAULT = os.environ.get('GITHUB_REPOSITORY', 'easyscience/diffraction-lib')`)
- **What:** Library use of `BadgeGenerator()` without arguments silently targets
  `easyscience/diffraction-lib` (the project badgery was extracted from). The
  CLI always passes `--repo`, so this only bites API users — but it bites
  silently, together with that project's token fallback (H1).
- **Fix:** Require `repo` explicitly (no default), or default to `None` and
  raise a clear error when unset.

### M9. Dashboard build workflow is fragile for common branch situations

- **Where:** `.github/workflows/dashboard.yaml:41-57,64-76`
- **What:** `git worktree add ../worktree-$BRANCH origin/$BRANCH` fails the
  whole job when a listed branch doesn't exist on origin (e.g. no `develop` in a
  fork, deleted PR branch); `$BRANCH` is unquoted and used raw in paths — branch
  names with `/` (e.g. `feature/x`) produce nested worktree paths and publish
  directories that break the dedup check (`[ -d ../worktree-$BRANCH ]`) and the
  published URL; PRs from forks dispatch with a `ref` that may not exist in the
  base repo.
- **Fix:** Guard each branch
  (`git ls-remote --exit-code origin "$BRANCH" || continue`), quote variables,
  and sanitize branch names for filesystem/URL use (e.g. `${BRANCH//\//-}`).

### M10. Repository governance/automation files are missing

- **Where:** `.github/` contains only `workflows/`
- **What:** No `dependabot.yml` (actions and Python deps never get automated
  updates — directly related to M1), no `CONTRIBUTING.md`, no `SECURITY.md`
  (despite a security workflow), no `CODEOWNERS`, no issue/PR templates, no
  `CHANGELOG.md` (release notes live only in GitHub Releases). The label
  vocabulary is duplicated between `labels.yaml:21-28` and
  `release-notes.yaml:48-59` with no single source of truth.
- **Fix:** Add the standard set; generate/synchronize labels from one data file.

---

## Low

### L1. `.gitignore` bugs and gaps

- **Where:** `.gitignore:5` — the entry `.pyc` matches only a file literally
  named `.pyc`, not `*.pyc` files; `dist/` (created by `pixi run dist-build`)
  and the generated output (`BADGES.html`, `index.html`) are not ignored.
- **Fix:** `*.pyc`, `dist/`, `BADGES.html`, `index.html`.

### L2. Dead code kept to satisfy tooling

- **Where:** `src/badgery/badges.py:23-53` (`_badge`, `codecov_badge`,
  `codefactor_badge` — always return `''`, docstrings admit "unused by
  renderer", `_ = self.repo` exists only to appease a lint rule);
  `render.py:655-658` (base `render()` is a `@staticmethod` returning `''`,
  overridden by an _instance_ method in the subclass — a signature mismatch);
  the `refs()` machinery (see H4).
- **Fix:** Delete the stubs; make the base renderer abstract or merge the two
  renderer classes (there is only one real implementation).

### L3. SPDX headers are inconsistently applied; the updater tool only scans `src/`

- **Where:** `src/badgery/metrics.py:1` (missing header — the only `src` file
  without one), all 26 test files, `tools/update_spdx.py` itself;
  `tools/update_spdx.py:60` hardcodes `Path('src')`.
- **Fix:** Extend the tool to `tests/` and `tools/`, run it, and consider wiring
  it into the `quality` task so it can't drift.

### L4. Logging behavior hides useful information

- **Where:** `src/badgery/cli.py:118-119` — `load_settings_from_yaml()` (which
  logs "Config not found; using defaults") runs inside `parse_args()`, _before_
  `logging.basicConfig` at `cli.py:189`, so the message is never shown at
  default level; `cli.py:194` logs `' Using config %s'` with a stray leading
  space; `cli.py:200-204` downgrades all metric read failures to DEBUG, so at
  INFO level a misconfigured report path just yields silent "unknown" cards.
- **Fix:** Configure logging before loading settings; log metric read failures
  at WARNING with the resolved path.

### L5. Toolchain pinning inconsistencies

- **Where:** `pixi.toml:37` — `nodejs = "*"` while the comment says "pinned to a
  stable LTS"; `pixi.lock` is format v6 (pixi warns on every run: "run
  `pixi lock` to upgrade to v7"); dev dependencies in `pyproject.toml:28-39` are
  all unpinned.
- **Fix:** Pin nodejs to an LTS series (e.g. `22.*`), run `pixi lock`, consider
  lower bounds for dev tools.

### L6. Typing contracts are internally inconsistent

- **Where:** `src/badgery/_metrics/base.py:62-69` — `read_value`/`read_all` are
  annotated `-> Never` yet overridden with `-> None`/value-returning methods (an
  LSP violation any type checker would flag); `complexity.py:37`,
  `docstring.py:38`, `maintainability.py:38` annotate `path: str` but are called
  with `None` (`getattr(..., None)`); `docstring.py:64-69` — `format_value`
  annotated `-> str` returns the raw value unchanged when truthy. No `py.typed`
  marker is shipped, so consumers get no types at all despite the annotation
  effort.
- **Fix:** Correct the annotations (`str | None`, `-> None`), add `py.typed`,
  and run mypy/pyright in CI.

### L7. `_resolve_pattern` glob fallback is nondeterministic

- **Where:** `src/badgery/cli.py:59-65` — when the branch-substituted path
  doesn't exist, the first `parent.glob(pattern)` hit is used; `Path.glob` order
  is filesystem-dependent, so with multiple matches the chosen report is
  arbitrary. The `'**'`→branch substitution (`cli.py:54`) is surprising and
  undocumented (see M7).
- **Fix:** `sorted(...)[0]` for determinism; document or drop the `**` rule.

### L8. Prettier configuration gaps

- **Where:** `.prettierignore` contains only `pixi.lock` — locally generated
  `reports/**/*.json` and `dist/` would be reformatted by
  `pixi run nonpy-format-fix`; the config file is named `prettierrc.toml`
  (non-standard, no leading dot), so editor integrations won't auto-discover it
  — every invocation must pass `--config` explicitly.
- **Fix:** Ignore `reports/` and `dist/`; consider `.prettierrc.toml`.

### L9. `git tag --delete $(git tag)` fails on tagless clones

- **Where:** `.github/workflows/test.yaml:67-69`
- **What:** On a fork (or any clone without tags) the command expands to
  `git tag --delete` with no arguments and exits non-zero, failing the job.
- **Fix:** `git tag | xargs -r git tag --delete` (or guard with a count).

### L10. `labels.yaml` interpolates event data into shell and misses the `reopened` event

- **Where:** `.github/workflows/labels.yaml:19` —
  `PR_LABELS=$(echo '${{ toJson(...) }}' | jq ...)`: the expression is
  substituted _before_ the shell parses, so a label name containing a single
  quote breaks/injects into the script (label names are maintainer-controlled,
  hence low); `labels.yaml:8` — `types` omits `reopened`, so a reopened
  unlabeled PR passes the check.
- **Fix:** Pass the JSON via `env:` and reference `"$LABELS"`; add `reopened`.

### L11. Packaging metadata is dated/incomplete

- **Where:** `pyproject.toml:11` (`license = { text = 'MIT' }` — PEP 639 now
  prefers `license = 'MIT'` + `license-files`, and the license _classifier_ on
  line 15 is deprecated under it), no `Development Status` classifier, no
  `keywords`, `authors` has no contact (`pyproject.toml:9`),
  `[tool.hatch.metadata] allow-direct-references = true`
  (`pyproject.toml:71-72`) is a leftover with no direct references in the
  dependency list, and the `documentation` URL just points at the repo.
- **Fix:** Modernize the license declaration; add status/keywords; drop the
  hatch leftover.

---

## Lowest

### LL1. Several ruff rule comments describe the wrong rules

- **Where:** `pyproject.toml:167` — `G` is _flake8-logging-format_, not "Type
  annotation issues"; `pyproject.toml:184` — `TCH` is about
  `TYPE_CHECKING`-block imports, not "incompatible types"; `pyproject.toml:185`
  — `TD` is _flake8-todos_, not "Type definition issues".
- **Fix:** Correct the comments (they actively mislead maintainers tuning the
  lint config).

### LL2. `tools/update_spdx.py` docstring contradicts its own behavior

- **Where:** `tools/update_spdx.py:5` — "Ensures SPDX-License-Identifier is set
  to **BSD-3-Clause**" while the code writes MIT (line 17).

### LL3. `'codecove'` typo alias

- **Where:** `src/badgery/config.py:214` — a deliberate alias for a misspelling;
  it silently legitimizes bad configs. Drop it or warn.

### LL4. Stale comments and redundant trigger filters in workflows

- **Where:** `release-pr.yaml:5` (comment says "develop into **master**"; the
  actual PR title says main); `coverage.yaml:7`
  (`branches: [master, develop, '**']` — `'**'` subsumes the rest, and `master`
  doesn't exist); `test.yaml:8-10`/`quality.yaml:8-10` (`tags-ignore` is
  redundant once `branches` is specified; the comments reference
  `publish-pypi.yml`, which doesn't exist — see H9).

### LL5. Renderer string-construction oddities

- **Where:** `src/badgery/render.py:694-713` — escaped `\"` quotes inside a
  triple-quoted f-string (needless noise); `src/badgery/cli.py:19` —
  `BRANCH_TOKEN = '{' + 'branch' + '}'` string-concatenation obfuscation.

### LL6. `group_icon` implements its mapping twice

- **Where:** `src/badgery/config.py:156-184` — an exact-match dict followed by a
  substring-fallback chain that re-derives the same values; the first branch of
  the fallback (`'qualit'` → `fas fa-gauge`) assigns the value it already has.

### LL7. Copyright holder naming is inconsistent

- **Where:** `LICENSE:3` says "enhantica"; SPDX headers say "Badgery
  contributors". Harmless, but pick one form.

### LL8. `versioningit` fallback tag is a footgun

- **Where:** `pyproject.toml:98` — `default-tag = 'v999.0.0'` is exploited
  intentionally by `test.yaml:63-69` to out-version PyPI, but any _other_
  tagless build context (shallow clone, fork) silently produces version 999.0.0
  artifacts; worth a comment in `pyproject.toml` at minimum.

---

## What was checked and found healthy

For balance, these areas were explicitly verified and are in good shape:

- **Tests:** 61/61 pass in <1 s, fully offline (network is monkeypatched);
  well-partitioned by module; meaningful edge-case files.
- **Coverage:** 85.4% line+branch (gate: 80%); docstring coverage 85.6% (gate:
  80%).
- **Lint/format:** `ruff check` and `ruff format --check` are clean with a
  genuinely strict rule set (incl. `S` security rules, complexity ≤ 10);
  per-file test ignores are sensible.
- **Zero runtime dependencies** is real (stdlib only) — a legitimate selling
  point.
- **Layout:** clean `src/` layout, small focused `_metrics/` modules,
  `versioningit` tag-based versioning works (`v0.6.0` latest).
- **Branch/release model:** develop/main with automated backmerge and release
  PRs is coherent and labeled for changelog automation.
