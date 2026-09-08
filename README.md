# DnD Soundboard

A browser-based soundboard for tabletop role-playing sessions with music playlists, ambience layers, and instantly triggered SFX pads.

## Version

**Current: 0.3.0**

Version 0.3.0 adds the scene automation badge, synchronized SFX scene-start settings, improved playlist-loop navigation, updated documentation, and 100 English SFX generation prompts. See the [Release Notes](RELEASE_NOTES_0.3.0.md) for the changes since favicon support was introduced.

## Features

- Game libraries with separate audio categories
- Sessions within a game
- Scenes with groups, tags, and custom audio configuration
- Music playlists with:
  - playback, pause, and track selection
  - previous/next track controls
  - track loop, playlist loop, and loop-off modes
  - crossfade
- Multiple ambience layers with individual volume and fade controls
- SFX pads with:
  - customizable colors
  - pad names
  - hotkeys
  - poly, toggle, and restart modes
  - marking for automatic playback on scene change
- Scene automation for music, ambience, and SFX
- Automatic SFX automation synchronization:
  - marking at least one pad enables global SFX automation
  - unmarking the last pad disables it
  - disabling global SFX automation removes all pad markers
- Audio ducking for voice playback
- Master, bus, and pad volume controls
- Dark UI with German and English localization
- Existing favicon support for `favicon.ico` and `favicon.png`
- Compact scene automation badge with two opposing play triangles
- Bidirectional synchronization between marked SFX pads and the global scene-start setting
- Playlist-loop navigation that wraps **Next track** from the last track to the first
- 100 concise English prompts for generating SFX assets

## Requirements

- Python 3.10 or newer
- FastAPI
- Uvicorn
- A modern browser with Web Audio API support

Install Python dependencies according to your project setup, for example using an existing `requirements.txt` file.

## Start the Server

From the project directory:

```bash
python3 soundboard-server.py --games-dir ./library --host 0.0.0.0 --port 8000
```

Then open the following address in a browser:

```text
http://localhost:8000
```

To access the Soundboard from another device on the local network:

```text
http://<server-ip>:8000
```

## Library Structure

Audio files are organized by game and audio category:

```text
library/
└── <game-name>/
    ├── Musik/
    ├── Ambience/
    └── SFX/
```

The UI displays the filenames as available audio assets.

## UI Delivery and Favicons

The web UI can be served from different static UI layouts. The server automatically searches for favicons in these directories:

```text
ui-dist/
ui-dist/public/
ui-dist/static/
```

The following fallback locations are also checked:

- the directory next to the server file
- the current working directory

The available routes are:

```text
/favicon.ico
/favicon.png
```

The UI references both formats so browsers can use the appropriate favicon for the environment.

## Key Concepts

- **Game:** The top-level library scope.
- **Session:** A specific adventure, chapter, or play project within a game.
- **Scene:** A saved audio configuration for a particular moment.
- **Bank:** A collection of one audio category within a scene: music, ambience, or SFX.
- **Scene automation:** Audio that starts automatically when entering a scene.

## Development and Verification

After changing the server source, run at least a Python syntax check:

```bash
python3 -m py_compile soundboard-server.py
```

Also test the HTML UI in a current browser, especially after changes to audio events, scene changes, and hotkeys.
