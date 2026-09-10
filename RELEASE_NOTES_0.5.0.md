# Release Notes — Version 0.5.0

**Release date:** September 10, 2026

Version 0.5.0 expands the soundboard from individual SFX triggers into a more flexible scene and variation workflow. It adds additional trigger modes, configurable asset pools, improved scene automation, and more reliable state persistence across UI rerenders and page reloads.

## Highlights

- New SFX trigger modes: Random, Round Robin, and Hold
- Configurable asset pools for SFX pads
- Improved scene-change automation for Music, Ambience, and SFX
- More reliable pad settings menus with preserved scroll position and focus
- Persistent active game and session selection after a browser refresh
- Improved scene and session management
- Additional localization and accessibility improvements

## New SFX trigger modes

### Random

- A pad can choose a sound randomly from its configured asset pool.
- Random selection makes repeated effects less predictable and reduces noticeable repetition.
- Random can be enabled independently for a Round Robin pad.
- The pad keeps the name **Round Robin** while displaying a distinct monochrome shuffle symbol when Random is enabled.

### Round Robin

- A pad can play multiple related assets in a fixed sequence.
- Each trigger advances to the next asset in the configured pool.
- After the final asset, playback wraps around to the first asset.
- The current position is tracked per pad and can be reset when the scene configuration is changed.
- The pad name remains **Round Robin** regardless of the selected variation behavior.

### Hold

- The sound plays while the mouse button or assigned hotkey is held.
- Releasing the pointer or key stops the sound cleanly.
- Hold behavior is also protected against stuck playback when the window loses focus.

## SFX asset pools

- Pads can use more than one SFX asset.
- Asset pools can be selected and edited from the pad settings menu.
- The selected pool is used by Random and Round Robin playback.
- Existing pads remain compatible and continue to use their original asset when no additional pool is configured.
- Pool selection and playback settings are persisted with the scene.

## Scene automation

- Music, Ambience, and SFX automation can be configured at scene level.
- SFX pads can be marked individually for automatic playback on scene changes.
- SFX automation remains synchronized with the marked pads:
  - marking a pad enables SFX automation for the scene
  - removing the last marker disables SFX automation
  - disabling SFX automation clears the pad markers
- Scene activation preserves the intended distinction between manual playback and automatic scene playback.

## Improved pad settings menus

- The long `…` pad settings menu now preserves its scroll position during rerenders.
- Changing a setting such as the Random toggle no longer sends the menu back to the top.
- Focus and cursor position are preserved more reliably while editing pad settings.
- Clicking outside an open pad menu closes it without affecting controls elsewhere in the interface.
- The menu remains usable on smaller screens and with keyboard navigation.

## Persistent game and session selection

- The currently selected session is remembered per game in the browser.
- After pressing F5 or reopening the page, the previously active game and session are restored when they are still available.
- Creating, switching, duplicating, or deleting sessions updates the remembered selection accordingly.
- The application no longer automatically moves to the newest game after every refresh.

## Scene and session workflow

- Improved handling of game and session creation.
- More predictable scene selection after switching sessions.
- Better support for duplicating and organizing scenes.
- Scene and session state is refreshed more consistently after changes.

## Localization and accessibility

- Added and maintained German and English labels, descriptions, and hints for the new SFX modes and asset-pool controls.
- Mode symbols remain compact and readable in the pad UI.
- Random Round Robin uses a monochrome crossed-arrow symbol so the visual distinction does not depend on color.
- Keyboard hotkeys remain disabled while editing inputs, selects, buttons, and other interactive controls.
- Visible focus handling is preserved across rerenders.

## Compatibility and persistence

- Existing scenes and pads remain compatible.
- Existing pads continue to use their saved mode and asset configuration.
- Pads without an explicit asset pool continue to use their primary asset.
- No database migration is required for the new UI-level pad configuration.
- Scene changes continue to be persisted through the existing scene API.

## Verification

- Verified German and English localization paths for the new controls.
- Verified JavaScript syntax with `node --check`.
- Verified Random, Round Robin, and Hold mode handling.
- Verified asset-pool selection and persistence.
- Verified pad-menu scroll-position restoration after rerenders.
- Verified active game/session restoration after a browser refresh.
