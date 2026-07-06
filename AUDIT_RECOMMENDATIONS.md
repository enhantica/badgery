# Badgery — project audit: recommendations

Companion to `AUDIT_ISSUES.md` (2026-07-06). Issues are referenced as H1-H9 /
M1-M10 / L1-L11 / LL1-LL8 where a recommendation directly resolves one, but each
recommendation below is self-contained.

## 1. Immediate actions (do these first)

1. **Revoke and remove the committed Codecov token** (H1). Delete the literal
   fallback in `src/badgery/badges.py:84` and `src/badgery/render.py:265`,
   revoke `qtsB5Q5BXO` in the Codecov UI of the affected project, and build
   badge URLs without a `token` parameter when `CODECOV_TOKEN` is unset.
   Consider `git filter-repo` history rewriting only if the token is privileged;
   revocation is usually enough for a graphing token.
2. **Claim the `badgery` name on PyPI** (H2). Even before the release pipeline
   exists, publish a minimal valid release so the name in your README cannot be
   squatted. Until then, change the README install line to
   `pip install git+https://github.com/enhantica/badgery`.
3. **Escape all HTML output** (H7). One `html.escape()` call per interpolated
   value in `render.py` plus a regression test with a hostile branch name.
4. **Fix the scheduled cleanup inputs** (H6) with `|| 30` / `|| 6` fallback
   expressions before the next 1st-of-month run, and do one manual
   `dry_run: true` dispatch to confirm.

## 2. Configuration: replace the hand-written YAML parser

The custom parser in `config.py` is the project's biggest correctness liability
(H3): inline comments corrupt values and can silently re-enable disabled cards,
numbers stay strings, nesting is unsupported, and errors pass silently. Three
options, in order of preference:

- **Switch the config format to TOML** and parse with stdlib `tomllib`. This
  keeps the zero-dependency promise with an _exact_ parser. A `.badgery.toml`
  maps naturally (`[[cards]]` tables), and migration for existing users is
  mechanical. Keep reading the legacy YAML for a deprecation window.
- **Accept PyYAML as the single runtime dependency.** `yaml.safe_load` is ~one
  line and battle-tested; "zero dependencies" becomes "one, boring".
- **Minimum bar if the hand parser stays:** strip inline comments, parse
  int/float scalars, _warn loudly_ on unparseable lines and unknown keys, and
  document the supported subset in the README. Add regression tests for
  `enabled: false # comment` and friends.

Additionally, validate configs at load time: unknown card `type`, missing
`report`/`workflow` keys, and (when running inside a repo) a `workflow:` file
that doesn't exist in `.github/workflows/` should produce warnings. That
validation would have caught H9 immediately. A `badgery --check-config`
subcommand would make this available in CI.

## 3. Data acquisition: prefer APIs over badge scraping

Today statuses are obtained by regex-parsing badge SVG internals, serially, with
an 8-second timeout per request (M3). Recommended target state:

- **GitHub workflow status:** query the REST API
  (`GET /repos/{repo}/actions/workflows/{file}/runs?branch=...&per_page=1`)
  using `GITHUB_TOKEN` when available; fall back to badge scraping without a
  token. Stable contract, gives you real conclusions (success/failure/
  cancelled) instead of a fixed word list.
- **Codecov:** use the public API v2
  (`/api/v2/github/{owner}/repos/{repo}/branches/{branch}`) rather than the
  badge SVG; it returns exact coverage and respects flags.
- **Concurrency + caching:** fetch all URLs with a small `ThreadPoolExecutor`
  and memoize by URL — the same badge is currently fetchable multiple times per
  render. Reduce the timeout to ~4 s with one retry. A full render should take a
  couple of seconds, not minutes.
- Log fetch failures at WARNING (with the URL) instead of DEBUG (L4), so an
  all-gray dashboard explains itself.

## 4. Release pipeline: make the dashboard's promises true

- Add **`publish-pypi.yaml`** using PyPI **Trusted Publishing** (OIDC — no
  long-lived token secret), triggered on `v*` tag push, with a `pypi`/`testpypi`
  environment split; add **`test-pypi.yaml`** that installs the published
  package and runs the test suite. These two files are already referenced by
  `.badgery.yaml` and workflow comments (H9), so the dashboard starts showing
  real data the moment they exist.
- Add a **Codecov upload step** (`codecov/codecov-action@v5`,
  `files: coverage-unit.xml`, `flags: unittests`) to `coverage.yaml` (H5) — the
  flag name must match the card's `flag: unittests`.
- Commit a **CHANGELOG.md** generated from the drafted release notes at release
  time, so history is readable outside GitHub Releases (M10).

## 5. CI: consolidate, restrict, and harden

- **One test workflow, real matrix** (H8, M4):
  `{ubuntu-latest, macos-latest, windows-latest} × {3.11, 3.12, 3.13, 3.14}` via
  pixi features (`py311`…`py314` already trivially expressible). Run the full
  matrix on PRs to `main`/`develop` and pushes to those branches; a single
  ubuntu+3.13 job is fine for feature-branch pushes if you keep them.
- **Trigger hygiene** (M4): drop the `push: ['**']` + `pull_request: ['**']`
  double-fire — use `pull_request` for branches, `push` for `main`/`develop`
  only; dispatch the dashboard from exactly one place; add `paths-ignore` for
  docs-only changes.
- **Supply chain** (M1, M2, M10): pin every action to a commit SHA with a
  version comment; add `.github/dependabot.yml` for `github-actions` and `pip`;
  declare least-privilege `permissions:` in every workflow (`contents: read`
  baseline, `security-events: write` where SARIF is uploaded); replace
  `github/ossar-action@main` with **CodeQL** + `zizmor` (workflow linter) +
  `pip-audit` in a scheduled security workflow that also runs on pushes to
  `main`/`develop`, so the security card has per-branch data.
- **Robustness** (M9, L9): guard the dashboard worktree loop with
  `git ls-remote --exit-code`, quote `$BRANCH`, sanitize `/` in branch names for
  paths/URLs; replace `git tag --delete $(git tag)` with
  `git tag | xargs -r git tag --delete`.

## 6. Development environment

- Replace the self-referential git dependency + `PYTHONPATH` shadowing with an
  **editable path install** in pixi
  (`badgery = { path = ".", editable = true, extras = ["dev"] }`) (M5), then
  delete the activation-env hack in `pixi.toml` and the `sys.path` shim in
  `tests/conftest.py`. One mechanism, no split-brain between installed and
  source code, offline-friendly.
- Run `pixi lock` to upgrade the lock format (the v6 warning prints on every
  command today), and pin `nodejs` to an LTS series to match its comment (L5).
- Consider a `pre-commit` hook config mirroring the `quality` task so formatting
  issues never reach CI.

## 7. Code health

- **Delete the dead badge API** (H4, L2): remove `BaseMetric.badge()`/ `refs()`,
  `GithubWorkflowMetric.badge()`, and the empty `BadgeGenerator` stubs; merge
  `HTMLDashboardRenderer` and `HTMLDashboardRendererWithSpec` into one class
  (there is only one real renderer) and drop the placeholder static `render()`.
- **Retire "master" internally** (M6): rename the value slots to
  `default/develop/feature`, key the renderer on those, default `default_branch`
  to `'main'`, and drop the `'master'` special-case in badge URLs. Keep
  accepting the old `CI_*_MASTER` env vars for one release with a deprecation
  warning, introducing `BADGERY_*`-prefixed replacements (M7).
- **Model config as data**: a small `@dataclass CardSpec` (type, title, group,
  report, workflow, flag, enabled) built centrally with validation replaces the
  dict-passing and makes unknown-key warnings natural. `metric_by_key`
  collisions (two cards, same key) then become detectable.
- **Typing**: fix the `Never`/`str`/`None` annotation mismatches (L6), ship a
  `py.typed` marker, and add mypy (or pyright) to the quality workflow — the
  codebase is fully annotated already; you're one config block away from getting
  value out of it.
- **Templating**: move the HTML/CSS out of Python string literals into a
  `string.Template` (stdlib) file packaged as data. This kills the escaped-
  quote noise (LL5), makes the CSS editable/lintable, and separates paint from
  logic. Self-host or subset the Font Awesome icons (or switch to inline SVG /
  emoji) so dashboards render offline and without a third-party CDN dependency.
- Housekeeping batch: `.gitignore` fixes (L1), SPDX headers everywhere + extend
  `update_spdx.py` to `tests/`+`tools/` and hook it into the `quality` task
  (L3), correct the wrong ruff-rule comments (LL1), fix the `update_spdx.py`
  docstring (LL2), drop the `'codecove'` alias with a warning (LL3), tidy stale
  workflow comments/filters (LL4), deduplicate `group_icon` (LL6).

## 8. Documentation and UX

- **Show the product**: add a screenshot (or small GIF) of a rendered dashboard
  at the top of the README — it's a visual tool with no visual in its docs (M7).
- **Reference section** in the README or `docs/`: table of card types and their
  accepted keys (including the `workflow:`/`file:` alias), the `{branch}` and
  `**` path substitutions, all supported env vars, exit behavior, and a
  copy-paste GitHub Actions snippet showing the reports-then-render flow (the
  `dashboard.yaml` in this repo is effectively the tutorial — distill it).
- Unify the output-name story: either default `--output` to `index.html` or show
  `BADGES.html` in the CI example, so the default and the documented usage
  match.
- Add `CONTRIBUTING.md` (pixi task cheatsheet: `quality`, `tests`, `coverage`),
  `SECURITY.md` (private reporting channel), `CODEOWNERS`, and minimal issue/PR
  templates (M10). The PR-label requirement enforced by `labels.yaml` belongs in
  `CONTRIBUTING.md`, since today contributors only discover it by failing the
  check.

## 9. Testing

- Add regression tests for the fixed bugs: inline-comment parsing (H3), HTML
  escaping of titles/branch names (H7), and — if the badge API is kept — a test
  that `refs()` works for every metric type (H4).
- Add one true end-to-end CLI test: write a config + fake reports to `tmp_path`,
  run `main()` with patched network, and assert on the written HTML file.
  Current e2e coverage stops at the renderer class.
- Raise coverage where it is thinnest (`_metrics/counts.py` at 63%, `render.py`
  fetch paths) once dead code is removed — deleting H4/L2 code alone will lift
  the ratio.
- Consider `pytest-httpserver` (dev-only) for exercising `_fetch` against a real
  socket, including timeout and non-200 paths.

## 10. Suggested sequencing

| Phase | Content                                                                                     | Issues closed     |
| ----- | ------------------------------------------------------------------------------------------- | ----------------- |
| 1     | Token removal + revocation, PyPI name claim, HTML escaping, cleanup-inputs fix              | H1 H2 H6 H7       |
| 2     | Codecov upload step, publish/test-pypi workflows, config validation warnings                | H5 H9             |
| 3     | Parser replacement (tomllib or PyYAML) + regression tests                                   | H3                |
| 4     | CI consolidation: matrix, triggers, SHA pinning, permissions, dependabot, CodeQL            | H8 M1 M2 M4 M10   |
| 5     | Dead-API deletion, master→default rename, editable install, API-based fetching with caching | H4 M3 M5 M6 M8 M9 |
| 6     | Docs (screenshot, reference), governance files, housekeeping batch                          | M7 L\* LL\*       |

Phases 1-2 are a day of work and remove all user-visible breakage; phase 3 is
the highest-value correctness investment; phases 4-6 are steady-state hardening
that can proceed PR by PR.
