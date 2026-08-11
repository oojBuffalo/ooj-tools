---
name: readme
description: This skill should be used when the user asks to "write a README", "generate a README for this repo/project", "improve/restructure this README", "add badges and sections to the README", or otherwise wants a standard, polished GitHub-style README produced from the actual repository. In Codex, use when the user invokes $readme.
---

# README

Produce or upgrade a repository's `README.md` by inspecting what the repo
actually is, then filling a standard GitHub-style structure — badges,
admonitions, and the section set a reader expects from a popular project.
These are guidelines to lean on for a quality result, not a rigid spec to
follow to the letter: keep only the sections a given repo earns, and drop the
rest rather than emitting empty headings.

## Section backbone

Every README gets the required (●) sections; add optional (○) ones only when
the repo has the substance for them.

| # | Section | | Notes |
|---|---------|---|-------|
| 1 | Title + tagline (H1) | ● | project name, one line under it |
| 2 | Badge row | ● | build / version / license / stack |
| 3 | Intro paragraph | ● | what it is, who it's for; optional `> [!TIP]` + key links |
| 4 | Nav row / TOC | ○ | savage-style `A · B · C` when long |
| 5 | Features / Why X | ○ | |
| 6 | Install / Setup | ● | prerequisites + steps, from the real toolchain |
| 7 | Usage / Quickstart | ● | a runnable example |
| 8 | Configuration | ○ | env vars, flags |
| 8.5 | Documentation | ○ (auto) | outbound links to docs site / guides / API |
| 9 | FAQ | ○ | reader-help; move to the tail if it grows long |
| 10 | Project Layout | ○ (auto) | pruned directory tree; merges into Architecture for app/service |
| 11 | Contributing | ● | link `CONTRIBUTING.md`, dev setup, how to run tests |
| 12 | License | ● | name + link to `LICENSE` |
| 13 | Acknowledgements / Contact | ○ | |

### Archetype inserts

Detect what kind of project it is and add the matching sections. Archetypes
**stack** — an app that is also a portfolio piece gets both sets (savage is
exactly this).

| Archetype | Signals | Adds |
|---|---|---|
| Library / package | `main`/`exports`/`module`, importable, published, no `bin` | API / reference, import-style Usage |
| CLI tool | `bin` field, `[project.scripts]`/`console_scripts`, click/commander/argparse | Commands & flags table |
| App / service | Dockerfile + compose, web-framework deps, server entrypoint, not published | Architecture (+ diagram), Deployment |
| Portfolio / demo | ADRs/design docs, a live-demo link, "assignment/screening" framing | Design Choices, Assumptions, What's Next, Limitations |

When signals are weak or conflicting, state your best guess and ask rather than
guessing silently.

## Badges

Use [shields.io](https://shields.io). Build the URLs from repo facts, order
them **status → version → license → stack**, and keep the default set to the
~4–6 that carry information. A longer logo wall of tech badges is optional
flair, not the default.

Detection-keyed core set:

- **Build status** — from `.github/workflows/` (Actions badge).
- **Version / release** — latest release tag, or package-registry version.
- **License** — from `LICENSE`.
- **Language / runtime** — primary language or framework version.
- **Package** — registry badge (npm, PyPI, crates.io) when published.

## Admonitions

GitHub alerts (`> [!TYPE]`) earn their place only when they carry something
easy to miss in plain text. Default **0–3** per README; never decorative.

| Alert | Use for |
|---|---|
| `> [!TIP]` | a shortcut or fast path (e.g. "just reviewing? use the live demo") |
| `> [!NOTE]` | a useful aside or non-blocking caveat |
| `> [!IMPORTANT]` | something the reader must know to succeed |
| `> [!WARNING]` | a likely failure or footgun |
| `> [!CAUTION]` | an irreversible or dangerous action |

## Inspect, then fill

Read the repo before writing a word. Map each fact to the section it feeds:

- **Manifests** (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`,
  `pom.xml`) → name, description, version, scripts, entry points, homepage.
- **`LICENSE`** → license badge + License section.
- **`.github/workflows/`** → build-status badge.
- **Lockfile / manifest** → the exact package manager for install commands.
- **File extensions + deps** → language, framework, archetype.
- **`Dockerfile` / `docker-compose`** → containerized setup, app/service signal.
- **`.env.example`** → Configuration env vars.
- **`Makefile` / `Taskfile`** → task commands for Setup/Usage.
- **`docs/`, `mkdocs.yml`, `docusaurus.config.*`, Sphinx `conf.py`** → Documentation.
- **Directory tree** → Project Layout (prune to meaningful dirs; respect
  `.gitignore`; drop `node_modules`/build output; one-line gloss per entry).
- **`CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` / `SECURITY.md`** → link them, do
  not duplicate their content.
- **Git remote** → repo URL and owner for links and badges.

**Never invent facts.** For an essential fact you cannot infer (the one-line
description when no manifest carries one, the primary usage example, the
license when there is no `LICENSE`), **pause and ask** — collect the gaps and
put them to the user in one batch. For merely optional gaps, leave a visible
`<!-- TODO: … -->` marker rather than interrogating or fabricating.

## Output

- **No README present** → generate `README.md`.
- **README already exists** → do **not** blind-overwrite. Read it, preserve
  what is worth keeping (hand-written prose, badges, links, custom sections),
  **augment and restructure** onto the backbone, show the plan, and write in
  place only after the user confirms. If the existing README contradicts what
  inspection found, surface the conflict instead of steamrolling it.

## Process

1. **Inspect** the repo per the read-list above.
2. **Detect** the primary archetype (and any secondary ones); confirm if unsure.
3. **Draft** each backbone + insert section from real facts — real install
   commands, real badges, a real directory tree.
4. **Add** badges and admonitions per the rules above.
5. **Resolve gaps** — ask for essential un-inferable facts in one batch; mark
   optional gaps with `<!-- TODO -->`.
6. **Confirm** the result (and the plan, if overwriting an existing README).
7. **Write** `README.md` in place.

## Template

A skeleton to adapt — delete what the repo does not earn, add archetype inserts
where they apply.

````markdown
# <Project Name>

<one-line tagline>

<!-- badges: status → version → license → stack -->
![Build](https://img.shields.io/github/actions/workflow/status/<owner>/<repo>/ci.yml)
![Version](https://img.shields.io/github/v/release/<owner>/<repo>)
![License](https://img.shields.io/github/license/<owner>/<repo>)

<what it is, who it's for — one short paragraph>

> [!TIP]
> <the fastest way to try it, if there is one>

[Setup](#setup) · [Usage](#usage) · [Contributing](#contributing) · [License](#license)

## Features
- <capability> <!-- optional -->

## Setup
```sh
<real install commands from the detected toolchain>
```

## Usage
```sh
<a runnable example>
```

## Configuration <!-- optional: from .env.example -->
| Variable | Default | Purpose |
|----------|---------|---------|
| `<VAR>`  | `<val>` | <!-- TODO --> |

## Documentation <!-- auto: when docs exist -->
- [Full docs](<url>) · [API reference](<url>) · [Changelog](CHANGELOG.md)

## Project Layout <!-- auto: non-trivial trees -->
```
<repo>/
├─ src/        # <gloss>
└─ tests/      # <gloss>
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md). Run the tests with `<test command>`.

## License
<SPDX name> — see [LICENSE](LICENSE).
````

## Example (app / service)

````markdown
# Widgetsmith

Self-hostable widget pipeline with a REST API and a React console.

![Build](https://img.shields.io/github/actions/workflow/status/acme/widgetsmith/ci.yml)
![License](https://img.shields.io/github/license/acme/widgetsmith)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)

Widgetsmith ingests raw widgets, normalizes them, and serves them over an
authenticated API. Built for single-site self-hosting.

> [!TIP]
> Just kicking the tires? `docker compose up` boots the whole stack with seed data.

[Setup](#setup) · [Architecture](#architecture) · [Usage](#usage) · [Contributing](#contributing) · [License](#license)

## Setup
```sh
cp .env.example .env
docker compose up
```

## Architecture
```
Browser ──HTTPS──► caddy ──/api/*──► api ──► Postgres
```
Caddy is the only container that publishes ports; the API and database stay on
the internal compose network.

## Usage
```sh
curl localhost:8080/api/widgets
```

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md). Run `make test` before opening a PR.

## License
MIT — see [LICENSE](LICENSE).
````
