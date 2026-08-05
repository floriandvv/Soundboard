# DnD Soundboard

A browser-based LAN soundboard for tabletop role-playing games. The Python server scans game-specific audio folders, exposes a small JSON API, stores scenes and sessions in SQLite, and serves a single-page web interface. Audio playback and mixing happen in the browser using Web Audio APIs.

## Features

- LAN-friendly web interface for live tabletop sessions
- Separate audio banks for **Music**, **Ambience**, and **SFX**
- Scene management with reusable music, ambience, and SFX configurations
- Sessions for selecting a curated subset of assets per game
- Browser-side playback with playlists, crossfades, loops, layers, fades, ducking, and polyphonic SFX pads
- English and German UI translations
- Stable UUID-based game and asset identifiers
- SQLite persistence for scenes and sessions
- Audio streaming with path validation
- Optional admin-token protection for write endpoints
- Basic request rate limiting, audit logging, security headers, and health checks

## Repository layout

```text
.
├── soundboard-server.py   # FastAPI application and API server
├── index.html             # Single-file browser UI
├── language.json          # English/German translations
├── .env.example           # Recommended local configuration template
├── requirements.txt       # Python runtime dependencies
├── library/               # Local audio libraries (keep out of Git)
├── ui-dist/               # Served UI directory in the default configuration
├── logs/                  # Optional rotating server logs
└── docs/
    ├── GETTING_STARTED.md
    └── INITIAL_COMMIT_MESSAGE.txt
```

## Quick start

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.venv\\Scripts\\Activate.ps1
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Prepare configuration

Copy `.env.example` to `.env` and adjust the values for your environment. Do not commit `.env` if it contains private tokens or machine-specific settings.

For a first local run, the defaults are sufficient. The server expects the UI files in `ui-dist/`, so create that directory and copy the UI files into it:

```bash
mkdir -p ui-dist
cp index.html language.json ui-dist/
```

### 4. Add audio files

Create one or more game folders below `library/`:

```text
library/
└── My Campaign/
    ├── Musik/
    │   ├── exploration.ogg
    │   └── battle.mp3
    ├── Ambience/
    │   └── forest.wav
    └── SFX/
        ├── sword-hit.wav
        └── door.ogg
```

The folder names `Musik`, `Ambience`, and `SFX` are part of the current server contract. Supported audio extensions are `.mp3`, `.wav`, `.ogg`, `.opus`, `.flac`, `.m4a`, and `.aac`.

### 5. Start the server

```bash
python soundboard-server.py
```

Open `http://127.0.0.1:8000` locally. For another device on the same network, open `http://<server-ip>:8000`.

Check the server with:

```bash
curl http://127.0.0.1:8000/api/health
```

## Configuration

The server accepts environment variables from `.env` and equivalent command-line flags:

| Variable | Default | Purpose |
|---|---:|---|
| `SOUNDBOARD_GAMES_DIR` | `./library` | Root folder containing game libraries |
| `SOUNDBOARD_DB` | `./soundboard.db` | SQLite database path |
| `SOUNDBOARD_UI_DIR` | `./ui-dist` | Folder containing `index.html` and `language.json` |
| `SOUNDBOARD_HOST` | `0.0.0.0` | Network bind address |
| `SOUNDBOARD_PORT` | `8000` | HTTP port |
| `SOUNDBOARD_LANGUAGE` | `en` | UI language: `en` or `de` |
| `SOUNDBOARD_ADMIN_TOKEN` | empty | Protects write endpoints when set |
| `SOUNDBOARD_CORS_ORIGINS` | `*` | Comma-separated allowed browser origins |
| `SOUNDBOARD_LOG_FILE` | empty | Optional rotating log file |
| `SOUNDBOARD_WRITE_RATE_LIMIT` | `60` | Maximum writes per client per minute |

## Operational and security notes

- This is designed for trusted LAN use, not as a public internet-facing service.
- Set `SOUNDBOARD_ADMIN_TOKEN` before exposing the server beyond a trusted local network.
- Replace the development CORS value `*` with exact origins in production.
- Use HTTPS and a reverse proxy if the service must cross an untrusted network.
- Back up `soundboard.db` and the `library/` directory together.
- Audio files are scanned lazily and the scan result is cached briefly; after adding files, reload the UI or wait for the cache to refresh.
- Browser autoplay policies require a user interaction. Click **Enable audio** before playback.
- Keep `.env`, the SQLite database, logs, and audio libraries out of version control unless there is a deliberate reason to publish them.

## API overview

- `GET /api/health` — database and scan status
- `GET /api/games` — available games
- `POST /api/games` — create a game folder
- `GET /api/library?game_id=<id>` — list scanned audio assets
- `GET /api/scenes?game_id=<id>` — list scenes
- `POST /api/scenes` — create or update a scene
- `PATCH /api/scenes/<scene_id>/order` — reorder a scene
- `DELETE /api/scenes/<scene_id>` — delete a scene
- `GET /api/sessions?game_id=<id>` — list sessions
- `POST /api/sessions` — create a session
- `GET /api/stream/<game_id>/<bucket>/<path>` — stream an audio asset

FastAPI also exposes interactive API documentation at `/docs` while the server is running.

## Development

Run the server with reload enabled during development:

```bash
uvicorn soundboard_server:app --reload
```

Because the application is currently implemented in `soundboard-server.py`, the simplest reliable development command remains:

```bash
python soundboard-server.py
```

Before publishing, consider adding automated tests for asset scanning, path traversal protection, scene validation, session isolation, and API authentication.

## License

As seen in the `LICENSE` file.
