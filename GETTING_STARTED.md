# Getting Started

This document is the first operational guide for the DnD Soundboard project.

## Prerequisites

- Python 3.10 or newer
- A modern browser with Web Audio API support
- Audio files in a browser-compatible format
- Optional: a local network if the soundboard is controlled from multiple devices

## First local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
mkdir -p ui-dist library logs
cp index.html language.json ui-dist/
python soundboard-server.py
```

Open `http://localhost:8000` and create or select a game. The server creates the game metadata file and the `Musik`, `Ambience`, and `SFX` folders when a game is created through the UI.

## Adding audio manually

The server scans this structure:

```text
library/<Game Name>/Musik/<file>
library/<Game Name>/Ambience/<file>
library/<Game Name>/SFX/<file>
```

Use descriptive filenames. Avoid moving files after scenes have been configured: asset IDs are stable for a given relative path, but changing a file's path creates a new asset identity.

## LAN operation

1. Start the server on the host machine.
2. Find the host's LAN IP address.
3. Make sure the firewall allows the configured TCP port.
4. Open `http://<host-ip>:8000` on the controller device.
5. Click **Enable audio** in the browser before starting playback.

Do not bind the service to a public interface without authentication and a suitable HTTPS/reverse-proxy setup.

## Configuration recommendations

For a shared LAN installation:

```dotenv
SOUNDBOARD_HOST=0.0.0.0
SOUNDBOARD_PORT=8000
SOUNDBOARD_LANGUAGE=en
SOUNDBOARD_ADMIN_TOKEN=replace-with-a-long-random-token
SOUNDBOARD_CORS_ORIGINS=http://192.168.1.50:8000
SOUNDBOARD_LOG_FILE=./logs/soundboard.log
```

Use a long random admin token and pass it in the `X-Admin-Token` header for write requests. Read-only requests do not require the token.

## Data and backup

The SQLite file stores sessions and scenes. Audio remains in the library directory. Back up both:

```bash
tar -czf soundboard-backup-$(date +%Y%m%d).tar.gz soundboard.db library/
```

Stop the server before a manual backup if scenes are being edited.

## Troubleshooting

### The page is empty or shows a missing UI

Verify that `SOUNDBOARD_UI_DIR` contains both `index.html` and `language.json`.

### The library is empty

Check the game folder names and confirm that audio files are inside exactly `Musik`, `Ambience`, or `SFX`. Confirm the file extension is supported.

### Audio does not start

Click **Enable audio**. This is required by browser autoplay policies. Also check the browser console and the `/api/health` endpoint.

### Other devices cannot connect

Use the host's LAN IP rather than `localhost`, verify `SOUNDBOARD_HOST=0.0.0.0`, and allow the port through the host firewall.

### Writes return `401 Unauthorized`

The server is configured with `SOUNDBOARD_ADMIN_TOKEN`. Supply the matching `X-Admin-Token` header or leave the token empty for a trusted local development setup.

## Suggested next steps

- Add unit and integration tests.
- Add a formal license.
- Split the single-file UI into a maintainable frontend build when the feature set grows.
- Add structured API schemas and generated client types.
- Add a production deployment example using a reverse proxy and HTTPS.
