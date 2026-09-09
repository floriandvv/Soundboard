# Release Notes — Version 0.4.0

**Release date:** September 9, 2026

Version 0.4.0 improves SFX control, audio-level management, keyboard interaction, localization, and the consistency of the transport controls.

## Highlights

- Per-pad SFX gain control in decibels
- New looping mode for SFX pads
- Reliable editing of numeric pad settings without triggering hotkeys
- Localized SFX settings and playback modes
- Consistent stop buttons across the audio banks
- Distinct symbols for Restart and Loop modes

## SFX pad gain

- Added an individual gain setting to every SFX pad.
- Gain can be set from **−60 dB to +12 dB**.
- The value is stored with the scene and remains available after reloading.
- Gain is applied to both supported SFX playback paths:
  - decoded Web Audio buffers
  - the HTML audio fallback used when a browser cannot decode the asset through Web Audio
- Invalid values are rejected with a localized validation message.

## New SFX Loop mode

- Added a fourth pad playback mode: **Loop**.
- First click starts the asset and repeats it continuously.
- Clicking the same pad again stops the loop.
- Loop mode works with both the decoded-buffer path and the HTML audio fallback.
- The mode is available in the pad settings menu and is displayed on the pad.
- Added German and English labels and hints for the new mode.

### SFX playback modes

- **Poly:** Each click starts an additional playback instance.
- **Toggle:** One click starts playback; the next click stops it.
- **Restart:** A new click starts the sound again from the beginning.
- **Loop:** One click starts continuous repetition; the next click stops it.

## Keyboard and focus handling

- Fixed a problem where typing numbers into the SFX gain field triggered a pad hotkey at the same time.
- Global SFX hotkeys are now ignored while focus is inside an input, textarea, select, or button.
- Added a stable focus key for the per-pad gain field.
- Focus, cursor position, and the current input value survive UI rerenders more reliably.
- Intermediate numeric editing states are no longer immediately overwritten while typing.

## Localization

- Added localized strings for:
  - SFX gain
  - gain help text
  - invalid gain values
  - Loop mode
  - Loop mode help text
- Improved fallback resolution so keys from the selected language are used before English fallback text.
- Prevented technical translation keys from appearing in the UI when a locale file is incomplete.

## Audio control UI

- Standardized the visible stop controls for Music, Ambience, and SFX.
- Stop buttons use the same compact `■ Stop` treatment and consistent sizing.
- Stop labels and tooltips remain localized.

## Playback symbols

- Restart now uses the monochrome bent-arrow symbol **`↪︎`**.
- Loop continues to use the circular repeat symbol **`↻`**.
- This makes Restart and Loop visually distinct while keeping the pad mode display compact.

## Compatibility and persistence

- Existing scenes remain compatible.
- Existing pads without an explicit gain continue to use `0 dB`.
- Existing pads without the new mode continue to use their saved mode, with `poly` remaining the default for newly created pads.
- No database migration is required; pad settings are persisted through the existing scene payload.

## Verification

- Verified German and English locale JSON files.
- Verified JavaScript syntax with `node --check`.
- Verified the gain range, localized keys, Loop mode selection, both loop-capable audio paths, and the keyboard-focus guard.
- Verified that the updated HTML and locale files were delivered together.
