# Badgery

Turn code metrics and CI results into a sleek, card‑based HTML dashboard.

Badgery reads reports you already generate in CI (Radon, Interrogate) and pulls
live badges (Codecov, CodeFactor, GitHub Actions) to produce a compact, static
HTML page of status cards. It compares your default branch, develop, and the
current feature branch side by side — perfect for PRs, dashboards, and GitHub
Pages.

## Features

- Cards: complexity, maintainability, docstring coverage, LOC, files/functions
- Integrations: Codecov, CodeFactor, GitHub Actions workflow status
- Branch comparison: default, develop, and feature
- Zero server: outputs a single HTML file you can publish anywhere
- Simple config: declarative `.badgery.yaml` with sensible defaults

## Install

```bash
pip install -U badgery
```

## Quick start

1. Add a minimal `.badgery.yaml` to your repo:

   ```yaml
   default_branch: main
   develop_branch: develop
   cards:
     - type: interrogate # docstring coverage (text report)
       report: reports/{branch}/coverage-docstring.txt
     - type: radon_cc # cyclomatic complexity (JSON)
       report: reports/{branch}/cyclomatic-complexity.json
     - type: radon_mi # maintainability index (JSON)
       report: reports/{branch}/maintainability-index.json
     - type: gh_action # GitHub Actions workflow status
       title: Tests
       workflow: test.yaml
   ```

2. Render the dashboard in CI (or locally):

   ```bash
   badgery --repo org/repo --branch branch --output index.html
   ```

Tip: Publish `index.html` with GitHub Pages for a persistent, shareable view.

## License

MIT
