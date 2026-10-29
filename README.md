# LibCloud

Generates an SVG logo cloud from your GitHub repositories' dependencies.

Scans manifests across your repos, filters dev noise, maps packages to canonical icons, and renders an Archimedean spiral SVG with logos sized by frequency.

---

## Features

- **Manifests parsed**: `package.json` (npm/pnpm/yarn/bun), `pyproject.toml`, `requirements.txt`, Maven `pom.xml`, and Docker (`Dockerfile`, `docker-compose.yml`).
- **Noise filtering**: Excludes test runners, linters, type stubs, and low-level transport shims.
- **Normalization**: Groups aliases and SDKs (`boto3` → AWS SDK, `google-api-python-client` → Google, `axois` → Axios).
- **Icon resolution**: Multi-tier lookup via cache, CDNs (Devicon, SimpleIcons, Iconify), PyPI/npm metadata, and website favicons.
- **Presets**: Paper, Ink, Graph, Techy, and Space, each with live canvas and matching SVG/PNG export.
- **Sizes**: Web (1400×900), README card (920×540), and Social (1200×630).
- **Ops dashboard**: Protected, read-only run history with failure, unnormalized, and filtered-package grouping.

---

## Setup

```bash
# Clone
git clone https://github.com/DineshThumma9/LibCloud.git
cd LibCloud

# Install dependencies
uv sync
```

### Configuration (`.env`)

```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env`:

```env
GITHUB_USERNAME=your-username
GITHUB_TOKEN=ghp_yourToken     # Optional, avoids GitHub API rate limits

# MongoDB (stores icon cache and ops run records; cache falls back to memory if unavailable)
MONGO_URI=mongodb://admin:secretpassword@localhost:27017/my_mongodb?authSource=admin

# Ops dashboard (/ops), protected with HTTP Basic auth.
# Leave either value empty to keep the dashboard disabled.
OPS_USER=admin
OPS_PASSWORD=change-me
```

---

## Usage

### CLI Pipeline

Runs the full pipeline, saves SVGs, and outputs audit CSVs:

```bash
uv run python scripts/pipeline_demo.py
```

Outputs are written under `data/runs/<username>/<run_id>/`:
- `output.svg`: Web full-view preset (1400×900)
- `output_readme.svg`: README preset (920×540)
- `resolved.csv`: Resolved technologies and counts
- `failed_icons.csv`: Unresolved packages

Web runs do not write report files. Their summaries and audit rows are stored in MongoDB
(`runs`, `run_resolved`, `run_failures`, `run_unnormalized`, `run_filtered`, `run_validation`).

### Web Server

Start the FastAPI app:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Endpoint: `GET /libcloud`

Streams scan progress as Server-Sent Events (`text/event-stream`).

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `username` | `str` | Required | GitHub username |
| `token` | `str` | `None` | Optional GitHub PAT; a bearer `Authorization` header is also accepted |

The web client applies preset, size, sort, and max-logos settings locally.
Only `username` and the bearer token affect a scan.

### Ops dashboard (`/ops`)

The ops dashboard is a read-only React page in the Vite app. The page asks for
credentials, verifies them against `/api/ops/summary`, and sends them as HTTP
Basic auth on every API request. Credentials are kept in browser
`sessionStorage` for the tab and cleared on sign out.

Set both credentials before starting the backend:

```env
OPS_USER=admin
OPS_PASSWORD=a-long-random-password
```

If either value is empty, `/api/ops/*` returns `503` and the login form shows
the unconfigured-server message. The React page shell itself contains no data;
run records are only returned by authenticated API calls. The page adds a
`noindex, nofollow` meta tag, and every API response also carries
`X-Robots-Tag: noindex, nofollow`, `Cache-Control: no-store`, and a restrictive
CSP.

Pages:

| Path | Purpose |
| :--- | :--- |
| `/ops` | Overview: run counts, resolution rates, recent runs, users |
| `/ops/runs` | Full run history, filterable by username |
| `/ops/runs/{run_id}` | Run summary, detail tabs, and per-kind CSV exports |
| `/ops/failed` | Failed icons grouped by canonical name and reason |
| `/ops/unnormalized` | Unnormalized packages grouped by cleaned name |
| `/ops/filtered` | Noise-blocklist and unsupported-manifest records |
| `/ops/search?q=` | Search names, slugs, reasons, origins, and validation URLs |

JSON API (same Basic auth):

```text
GET /api/ops/summary
GET /api/ops/runs?username=<user>&limit=<n>
GET /api/ops/runs/{run_id}
GET /api/ops/details/{kind}?username=<user>&limit=<n>
GET /api/ops/search?q=<query>&limit=<n>
GET /api/ops/runs/{run_id}/{kind}.csv
```

`kind` is one of `resolved`, `failures`, `unnormalized`, `filtered`, or
`validation`. Run data is read from MongoDB. If Mongo is unavailable, the
process falls back to the in-memory run cache populated by scans in that same
process. Tokens and request params are never exposed; token-like strings are
redacted and manifest paths are reduced to filenames.

In development, Vite proxies `/api` to the FastAPI server. When serving the
production build, configure the static server to fall back to `index.html` for
`/ops` and `/ops/*` so direct links and reloads work.

---

## Embed in GitHub README

Use the **Export & share** panel in the web app to create a share snapshot. It
copies Markdown in this shape:

```markdown
[![My Tech Stack](https://your-domain.com/s/abc123/cloud.svg)](https://your-domain.com/s/abc123)
```

Shares are stored snapshots. Re-run the scan and create a new share after icon
or normalization fixes.

---

## Architecture

```mermaid
flowchart TD
    A["GitHub User / Token"] --> B["GitHub API (GraphQL / Git-clone)"]
    B --> C["DependencyParser (package.json, pyproject, pom.xml, docker)"]
    C --> D["Noise Filter & Canonical Normalizer"]
    D --> E["ImageResolver (MongoDB, CDNs, Registry / Favicon Fallback)"]
    E --> F["transform_wordcloud (Archimedean Spiral Layout)"]
    F --> G["output.svg (Web) / output_readme.svg (README)"]
```
