# Release Notes — Version 0.3.0

**Release date:** September 8, 2026

## Overview

Version 0.3.0 improves favicon support in the Soundboard and makes web UI delivery more robust across different deployment layouts.

## Changes

- Added support for both favicon formats:
  - `favicon.ico`
  - `favicon.png`
- Added FastAPI routes for serving the favicons:
  - `GET /favicon.ico`
  - `GET /favicon.png`
- Added automatic favicon discovery in the configured UI directory.
- The following UI directories are supported:
  - `ui-dist/`
  - `ui-dist/public/`
  - `ui-dist/static/`
- Added fallback favicon lookup:
  - next to the server file
  - in the current working directory
- Referenced both favicon formats in the HTML document `<head>`.
- Added a minimalist Soundboard favicon as a PNG asset.
- Verified the server source with a Python syntax check.
- Improved favicon support for different UI deployment layouts.

## Technical Details

The server searches for favicon files in a defined order. This allows browser and tab icon delivery to work with both built UIs and alternative static directory layouts.

The HTML UI references both formats:

```html
<link rel="icon" href="/favicon.ico" type="image/x-icon" sizes="any" />
<link rel="icon" href="/favicon.png" type="image/png" />
```

## Verification

- Successfully ran a Python syntax check on the server source.
- Documented both favicon routes and the extended search paths.
- Existing UI functionality remains unchanged.

## Upgrade Notes

No database changes are required to upgrade to version 0.3.0. Make sure that at least one supported favicon file is present in one of the directories checked by the server.
