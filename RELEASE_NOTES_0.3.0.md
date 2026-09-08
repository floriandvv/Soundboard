# Release Notes — Version 0.3.0

**Release date:** September 8, 2026

## Changes since favicon support

### Scene automation indicator

- Added a compact automation badge to the scene overview.
- Replaced the previous multi-dot indicator with two opposing play triangles.
- Removed the surrounding circle from the scene badge for a cleaner visual treatment.
- Kept the badge available as a quick indication that a scene contains automatic audio actions.

### SFX automation synchronization

- Added bidirectional synchronization between the global SFX scene-start setting and individual pad markers.
- Marking at least one SFX pad automatically enables **Start marked SFX on scene change**.
- Unmarking the last SFX pad automatically disables the global setting.
- Disabling the global setting removes all SFX pad markers.
- Removing a marked pad recalculates the global SFX automation state.
- This prevents contradictory states between the global setting and individual SFX pads.

### Playlist navigation

- Improved the **Next track** behavior for playlist loop mode.
- When the last track is active and playlist loop is enabled, pressing **Next track** now starts the first track again.
- Without playlist loop, the last track remains selected instead of wrapping around.

### Documentation and SFX content

- Updated the README and user manual with the current playback, scene automation, SFX synchronization, and playlist behavior.
- Added assets for the SFX bank.

## Upgrade Notes

No database changes are required for these updates. Existing scenes continue to work, while SFX automation states are normalized when scenes are loaded or edited.
