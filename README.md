# DnD Soundboard

A browser-based soundboard for tabletop role-playing sessions with music playlists, ambience layers, and instantly triggered SFX pads.

![DnD Soundboard screenshot](assets/screenshot.png)

## Version

**Current: 0.5.0**

0.5.0 — Adds Random, Round Robin, and Hold SFX modes, configurable asset pools, improved scene automation, persistent pad-menu state, and restoration of the active game and session after refresh.

See [Release Notes 0.5.0](RELEASE_NOTES_0.5.0.md) for the complete change list.

## Features

- Game libraries with separate audio categories
- Sessions within a game
- Scenes with groups, tags, and custom audio configuration
- Music playlists with:
  - playback, pause, and track selection
  - previous/next track controls
  - track loop, playlist loop, and loop-off modes
  - crossfade
- Multiple ambience layers with:
  - independent on/off control
  - individual volume
  - fade duration
  - scene-change automation
- SFX pads with:
  - customizable colors
  - editable pad names
  - hotkeys
  - individual gain from −60 dB to +12 dB
  - poly, toggle, restart, and loop modes
  - marking for automatic playback on scene change
- Six SFX playback modes:
  - **Poly:** Each click starts an additional playback instance.
  - **Toggle:** One click starts playback; the next click stops it.
  - **Restart:** A new click starts the sound again from the beginning.
  - **Loop:** One click starts continuous repetition; the next click stops it.
  - **Round Robin:** Each click starts a different asset from a pool; Random option available.
  - **Hold:** As long as the pad or shortkey is pressed the asset plays.
- Scene automation for music, ambience, and SFX
- Automatic SFX automation synchronization:
  - marking at least one pad enables global SFX automation
  - unmarking the last pad disables it
  - disabling global SFX automation removes all pad markers
- Audio ducking for voice playback
- Master, bus, layer, and pad volume controls
- German and English localization
- Localized validation and help text for SFX gain and Loop mode
- Focus-preserving pad settings menus
- Global hotkeys disabled while editing form fields
- Compact scene automation badge with two opposing play triangles
- Consistent stop controls for Music, Ambience, and SFX
- Existing favicon support for `favicon.ico` and `favicon.png`

# DnD Soundboard

A browser-based soundboard for tabletop role-playing sessions with music playlists, ambience layers, and instantly triggered SFX pads.

## Version

Current: 0.5.0 — Adds Random, Round Robin, and Hold SFX modes, configurable asset pools, improved scene automation, persistent pad-menu state, and restoration of the active game and session after refresh.

See Release Notes 0.5.0 for the complete change list.

## Features

- Game libraries with separate audio categories
- Sessions within a game
- Scenes with groups, tags, and custom audio configuration
- Music playlists with:

  
  - playback, pause, and track selection
  - previous/next track controls
  - track loop, playlist loop, and loop-off modes
  - crossfade
- Multiple ambience layers with:

  
  - independent on/off control
  - individual volume
  - fade duration
  - scene-change automation
- SFX pads with:

  
  - customizable colors
  - editable pad names
  - hotkeys
  - individual gain from −60 dB to +12 dB
  - poly, toggle, restart, and loop modes
  - marking for automatic playback on scene change
- Four SFX playback modes:

  
  - **Poly:** Each click starts an additional playback instance.
  - **Toggle:** One click starts playback; the next click stops it.
  - **Restart:** A new click starts the sound again from the beginning.
  - **Loop:** One click starts continuous repetition; the next click stops it.
- Scene automation for music, ambience, and SFX
- Automatic SFX automation synchronization:

  
  - marking at least one pad enables global SFX automation
  - unmarking the last pad disables it
  - disabling global SFX automation removes all pad markers
- Audio ducking for voice playback
- Master, bus, layer, and pad volume controls
- German and English localization
- Localized validation and help text for SFX gain and Loop mode
- Focus-preserving pad settings menus
- Global hotkeys disabled while editing form fields
- Compact scene automation badge with two opposing play triangles
- Consistent stop controls for Music, Ambience, and SFX
- Existing favicon support for `favicon.ico` and `favicon.png`
- some SFX assets

## Repository layout

\`\`\`text

.

├── [soundboard-server.py](http://soundboard-server.py)   # FastAPI application and API server

├── .env                   # Local configuration; keep private

├── library/               # Local audio libraries (keep out of Git)

├── locale/

```
├── de.json                # German translations (copied to ui-dist/locale/)

└── en.json                # English translations (copied to ui-dist/locale/)
```

├── ui-dist/               # Served UI directory in the default configuration

```
├── index.html             # Single-file browser UI

└── favicon.ico
```

└── logs/                  # Optional rotating server logs

\`\`\`

## Quick start

### 1. Create a virtual environment

\`\`\`bash

python3 -m venv .venv

source .venv/bin/activate

\`\`\`

On Windows PowerShell:

\`\`\`powershell

py -m venv .venv

.venv\\\\Scripts\\\\Activate.ps1

\`\`\`

### 2. Install dependencies

The server has two direct Python runtime dependencies:

- `fastapi>=0.115,<1.0` — HTTP API, middleware, and static file serving
- `uvicorn[standard]>=0.30,<1.0` — ASGI server used to run the application

Install them directly from the README:

\`\`\`bash

python -m pip install --upgrade pip

python -m pip install "fastapi&gt;=0.115,&lt;1.0" "uvicorn\[standard\]&gt;=0.30,&lt;1.0"

\`\`\`

A separate dependency file is not required for setup because the complete dependency list is documented above.

### 3. Prepare configuration

Create a local `.env` file and adjust the values for your environment. Do not commit `.env` if it contains private tokens or machine-specific settings.

For a first local run, the defaults are sufficient. The server expects the UI files in `ui-dist/`, so create that directory and copy the UI files into it:

\`\`\`bash

mkdir -p ui-dist/locale

cp index.html favicon.png ui-dist/

cp de.json en.json ui-dist/locale/

\`\`\`

### 4. Add audio files

Create one or more game folders below `library/`:


library/

└── My Campaign/
    ├── Musik/
      ├── exploration.ogg
      └── battle.mp3
    ├── Ambience/
      └── forest.wav
    └── SFX/
      ├── sword-hit.wav
      └── door.ogg

The folder names `Musik`, `Ambience`, and `SFX` are part of the current server contract. Supported audio extensions are `.mp3`, `.wav`, `.ogg`, `.opus`, `.flac`, `.m4a`, and `.aac`.

### 5. Start the server

\`\`\`bash

python [soundboard-server.py](http://soundboard-server.py)

\`\`\`

Open `http://127.0.0.1:8000` locally. For another device on the same network, open `http://<server-ip>:8000`.

Check the server with:

\`\`\`bash

curl [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

\`\`\`

## Configuration

The server accepts environment variables from `.env` and equivalent command-line flags:

| Variable | Default | Purpose |

|---|---:|---|

| `SOUNDBOARD_GAMES_DIR` | `./library` | Root folder containing game libraries |

| `SOUNDBOARD_DB` | `./soundboard.db` | SQLite database path |

| `SOUNDBOARD_UI_DIR` | `./ui-dist` | Folder containing `index.html` and the `locale/` directory |

| `SOUNDBOARD_HOST` | `0.0.0.0` | Network bind address |

| `SOUNDBOARD_PORT` | `8000` | HTTP port |

| `SOUNDBOARD_LANGUAGE` | `en` | Default UI language; must match a file in `locale/` |

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
