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
- Distinct mode symbols:
  - **Restart:** `↪︎`
  - **Loop:** `↻`
- Existing favicon support for `favicon.ico` and `favicon.png`
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

## Key Concepts

- **Game:** The top-level library scope.
- **Session:** A specific adventure, chapter, or play project within a game.
- **Scene:** A saved audio configuration for a particular moment.
- **Bank:** A collection of one audio category within a scene: music, ambience, or SFX.
- **Scene automation:** Audio that starts automatically when entering a scene.
- **Pad gain:** The individual volume adjustment for one SFX pad, separate from the SFX bus volume.

## Playback Modes

The global playback control provides three modes:

- **Playback off:** Active audio sources are stopped.
- **Scene playback:** The active scene runs; changing scenes stops the previous playback.
- **Scene automation:** Music, ambience, and SFX marked for automation start when changing scenes.

## Music Playlist

### Adding Tracks

Add available music assets to the active scene's playlist. The order can be changed within the playlist.

### Playback Controls

The music card provides:

- play/pause
- previous track
- next track
- selection of a specific track
- crossfade control
- loop control
- music bus volume
- a dedicated stop button

### Loop Modes

The loop button cycles through:

1. **Loop off:** Playback ends after the last track.
2. **Track loop:** The current track repeats.
3. **Playlist loop:** The playlist starts again with the first track after the last track.

When playlist loop is active, the **Next track** button also returns to the first track after the last track.

## Ambience

Ambience consists of multiple layers that can run simultaneously.

Each layer can provide controls for:

- on/off
- volume
- fade duration
- scene-change automation
- stopping all ambience layers

Ambience automation starts the selected layers when entering the scene.

## SFX Bank

### Adding SFX

Select available SFX assets from the library and add them to the scene's SFX bank.

### Using a Pad

A pad can be triggered by clicking it or pressing its assigned hotkey. The available modes are:

- **Poly:** Each click starts an additional playback instance.
- **Toggle:** One click starts playback and another click stops it.
- **Restart:** A new click starts the sound again from the beginning. It uses the `↪︎` symbol.
- **Loop:** One click starts the asset and repeats it continuously. Clicking the same pad again stops the loop. It uses the `↻` symbol.

Loop mode is implemented for both supported SFX playback paths: decoded Web Audio buffers and the HTML audio fallback.

### Configuring a Pad

The pad settings menu can be used to change:

- color
- visible name
- individual gain
- playback mode
- hotkey
- removing the pad from the scene

Pad gain accepts values from **−60 dB to +12 dB**. Existing pads without an explicit gain use `0 dB`.

### SFX Automation on Scene Change

Each pad can be marked for scene changes. Marked pads are triggered automatically when the corresponding scene starts.

The global **“Start marked SFX on scene change”** setting is automatically synchronized with the pad markers:

- Marking at least one pad enables the global setting.
- Unmarking the last marked pad disables the global setting.
- Disabling the global setting removes all pad markers.
- Removing a marked pad recalculates the global state.

This prevents contradictory states between the global setting and individual pads.

## Localization

The UI supports German and English.

Localized strings include:

- navigation and playback controls
- SFX pad modes
- SFX gain labels and help text
- gain validation messages
- Loop labels and help text
- scene automation controls
- stop buttons and tooltips

If a locale file is incomplete, the UI uses the selected language's fallback values before falling back to English.

## Keyboard Controls and Focus Handling

- Assigned hotkeys trigger their respective SFX pads.
- The spacebar can be used as a panic/stop control unless focus is inside an interactive form element.
- Global SFX hotkeys are ignored while focus is inside an input, textarea, select, or button.
- Pad settings retain focus and cursor position during UI rerenders.
- Interactive elements can be operated with `Tab` and `Enter`.

## Audio Routing

The application separates audio into the following levels:

- master volume
- music bus
- ambience bus
- SFX bus
- individual ambience-layer volume
- individual SFX-pad gain

SFX gain is applied to both the decoded buffer path and the HTML audio fallback before the signal reaches the SFX bus.

Ducking can lower background audio while voice playback is active and raise it again afterward.

## Favicon Support

Version 0.3.0 introduced support for:

```text
/favicon.ico
/favicon.png
```

The server automatically searches for favicon files in:

```text
ui-dist/
ui-dist/public/
ui-dist/static/
```

If no file is found there, it also checks the directory next to the server file and the current working directory.

## Verification

After changing the server source, run at least a Python syntax check:

```bash
python3 -m py_compile soundboard-server.py
```

For UI changes, also verify the HTML JavaScript syntax:

```bash
node --check <extracted-inline-script>.js
```

Test audio events, scene changes, pad modes, gain editing, localization, and hotkeys in a current browser.

## Upgrade Notes for 0.4.0

- No database migration is required.
- Existing scenes remain compatible.
- Existing pads without `gainDb` use `0 dB`.
- Existing pads keep their saved mode.
- Newly created pads default to `poly`.
- Existing locale files should include the new SFX gain and Loop translation keys; the UI also provides fallback values.
