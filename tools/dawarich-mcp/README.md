# dawarich-mcp

Self-hosted [Dawarich](https://github.com/Freika/dawarich) (a Google Timeline
replacement) plus a Model Context Protocol server so Claude can answer questions
about your travel history.

Google deprecated cloud Timeline in late 2024, so personal location history can't
be queried through any Google API anymore. The only data source available is the
~90 days currently on your phone, exported via the Google Maps app. Dawarich
ingests that export and exposes a REST API; this MCP wraps the API for Claude.

## Prereqs

- Docker (with `docker compose`)
- [`uv`](https://github.com/astral-sh/uv) for running the Python MCP server

## Stand up Dawarich

```sh
cd tools/dawarich-mcp
cp .env.example .env
# Fill in SECRET_KEY_BASE (openssl rand -hex 64) and POSTGRES_PASSWORD / DATABASE_PASSWORD.

docker compose up -d
docker compose ps   # wait for all four services to report "healthy"
```

Open `http://localhost:3000` and log in with the defaults:

- email: `demo@dawarich.app`
- password: `safepassword`

**Change that password immediately** (top-right profile → Account).

## Export Google Timeline from your phone

- **Android:** Settings → Location → Location services → Timeline → *Export Timeline data*
- **iOS:** Google Maps app → profile pic → Your Timeline → ⋯ → *Export Timeline data*

Transfer the resulting JSON to the machine running Dawarich.

## Import into Dawarich

In the Dawarich UI: *Imports* → **New** → source **"Google Phone Takeout"** →
upload the JSON.

> Uploads are capped at **5 MB per file**. If your export is bigger, split it:
> ```sh
> jq -c '.semanticSegments[0:500]' location-history.json > part1.json
> jq -c '.semanticSegments[500:1000]' location-history.json > part2.json
> ```
> …and upload each part. The actual top-level key may differ — `jq 'keys'` will
> tell you.

Imports run on the `dawarich_sidekiq` container. Tail it if a job stalls:
`docker compose logs -f dawarich_sidekiq`.

## Grab your API key

In Dawarich: profile menu → *Account* → copy the API key.

## Wire up the MCP server

The MCP server talks to Dawarich over its REST API. Register it with Claude Code:

```sh
claude mcp add dawarich \
  --env DAWARICH_BASE_URL=http://localhost:3000 \
  --env DAWARICH_API_KEY=<paste-your-key> \
  -- uv run --directory $(pwd)/server python -m dawarich_mcp
```

Or, equivalently, add this to your Claude Code MCP config by hand:

```json
{
  "mcpServers": {
    "dawarich": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/tools/dawarich-mcp/server",
        "python",
        "-m",
        "dawarich_mcp"
      ],
      "env": {
        "DAWARICH_BASE_URL": "http://localhost:3000",
        "DAWARICH_API_KEY": "..."
      }
    }
  }
}
```

Restart Claude Code. In a new session, ask:

> "What countries did I visit in the last 90 days?"

Claude should call `get_stats` and answer from your imported data.

## Tools exposed

| Tool | What it returns |
| --- | --- |
| `get_points(start_at, end_at, page, per_page)` | Raw GPS points, paginated |
| `get_visits(start_at, end_at)` | Stays at named places |
| `get_stats(year?, month?)` | Distance, countries, cities, point count |
| `list_imports()` | Status of uploaded Timeline files |
| `list_areas()` | User-defined geofences |
| `summarize_trips(start_at, end_at)` | Compact day-by-day visit summary |

All dates are ISO 8601 (`2025-07-01` or `2025-07-01T00:00:00Z`).

## Troubleshooting

- **`401` from the API.** Dawarich uses an `api_key` *query parameter*, not a
  bearer token. Check `DAWARICH_API_KEY` is set in the MCP env.
- **Import stuck at "scheduled".** Sidekiq isn't running or can't reach Postgres.
  `docker compose logs dawarich_sidekiq`.
- **UI loads but stats are empty.** Imports run asynchronously; check the
  *Imports* page in the UI for per-job status.
- **Can't reach UI from phone on the LAN.** Add your laptop's LAN IP to
  `APPLICATION_HOSTS` in `.env` and `docker compose up -d` to recreate the app
  container.
