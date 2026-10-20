# LibCloud

Generates an SVG logo cloud from your GitHub repositories' dependencies.

Scans manifests across your repos, filters dev noise, maps packages to canonical icons, and renders an Archimedean spiral SVG with logos sized by frequency.

---

## Features

- **Manifests parsed**: `package.json` (npm/pnpm/yarn/bun), `pyproject.toml`, `requirements.txt`, Maven `pom.xml`, and Docker (`Dockerfile`, `docker-compose.yml`).
- **Noise filtering**: Excludes test runners, linters, type stubs, and low-level transport shims.
- **Normalization**: Groups aliases and SDKs (`boto3` → AWS SDK, `google-api-python-client` → Google, `axois` → Axios).
- **Icon resolution**: Multi-tier lookup via cache, CDNs (Devicon, SimpleIcons, Iconify), PyPI/npm metadata, and website favicons.
- **Presets**:
  - `web` (1400×900): Full layout for browser view / web pages.
  - `readme` (920×540): Compact card sized for GitHub profile READMEs.

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

```env
GITHUB_USERNAME=your-username
GITHUB_TOKEN=ghp_yourToken     # Optional, avoids GitHub API rate limits

# MongoDB (Optional — falls back to in-memory cache if not running)
MONGO_URI=mongodb://admin:secretpassword@localhost:27017/my_mongodb?authSource=admin
```

---

## Usage

### CLI Pipeline

Runs the full pipeline, saves SVGs, and outputs audit CSVs:

```bash
PYTHONPATH=src uv run python src/test.py
```

Outputs:
- `src/output.svg`: Web full-view preset (1400×900)
- `src/output_readme.svg`: README preset (920×540)
- `output.csv`: Resolved technologies and counts
- `filtered_packages.csv`: Excluded noise dependencies
- `failed_icons.csv`: Unresolved packages

### Web Server

Start the FastAPI app:

```bash
PYTHONPATH=src uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Endpoint: `GET /framecloud`

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `username` | `str` | Required | GitHub username |
| `token` | `str` | `None` | Optional GitHub PAT |
| `preset` | `str` | `"web"` | `"web"` (1400×900) or `"readme"` (920×540) |
| `width` | `int` | `None` | Custom width in px |
| `height` | `int` | `None` | Custom height in px |
| `min_size` | `int` | `None` | Smallest logo size in px |
| `max_size` | `int` | `None` | Largest logo size in px |
| `padding` | `int` | `None` | Padding between logos in px |
| `max_logos` | `int` | `None` | Max logos to place (default: all) |
| `bg_color` | `str` | `"#1a1b26"` | Background hex color |

---

## Embed in GitHub README

```markdown
<!-- README Card Preset -->
![Tech Stack](https://your-domain.com/framecloud?username=DineshThumma9&preset=readme)

<!-- Full Web Preset -->
![Tech Universe](https://your-domain.com/framecloud?username=DineshThumma9&preset=web)
```

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
