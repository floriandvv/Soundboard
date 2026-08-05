#!/usr/bin/env python3
"""Soundboard Server (LAN) – FastAPI

- Hosts the web UI (static build) at /
- Streams audio assets from a folder structure:
    library/<GAME_NAME>/Musik
    library/<GAME_NAME>/Ambience
    library/<GAME_NAME>/SFX

- Provides JSON APIs for:
    - listing games + assets
    - listing/CRUD scenes

This is a starter server: it focuses on a clean, robust baseline.
Audio playback/mixing happens in the browser client (WebAudio).

Run:
  python3 soundboard-server.py --games-dir ./library --host 0.0.0.0 --port 8000

Then open from the laptop:
  http://<server-ip>:8000

Notes:
- Uses HTTP Range support for streaming via Starlette's FileResponse.
- Stores state in SQLite (default: ./soundboard.db).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


def load_dotenv(path: Optional[Path] = None) -> None:
    """Load simple KEY=VALUE settings without overriding real environment variables.

    Prefer an explicitly supplied file, then look next to this script and in the
    current working directory. This makes startup independent of the directory
    from which uvicorn/python is launched.
    """
    candidates = [path] if path is not None else [
        Path(__file__).resolve().parent / '.env',
        Path.cwd() / '.env',
    ]
    dotenv_path = next((candidate for candidate in candidates if candidate and candidate.exists()), None)
    if dotenv_path is None:
        return
    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


load_dotenv()


AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".opus", ".flac", ".m4a", ".aac"}
VALID_BUCKETS = {"Musik", "Ambience", "SFX"}
WRITE_PATHS = {"POST", "PATCH", "DELETE"}


def configure_logging(log_path: Optional[Path] = None) -> logging.Logger:
    logger = logging.getLogger("soundboard")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    handler: logging.Handler
    if log_path:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self.hits: Dict[str, deque[float]] = defaultdict(deque)

    def allowed(self, key: str) -> bool:
        now = time.time()
        bucket = self.hits[key]
        while bucket and now - bucket[0] >= self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "game"


@dataclass
class Asset:
    id: str
    game_id: str
    bucket: str
    filename: str
    rel_path: str
    size: int


def init_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")

    # Base tables. The project starts with a clean database; no legacy migration
    # is required. Sessions are the parent table for scenes and session_assets.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL,
          title TEXT NOT NULL,
          created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
          updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scenes (
          id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL,
          session_id TEXT,
          title TEXT NOT NULL,
          scene_group TEXT NOT NULL,
          tags_json TEXT NOT NULL,
          music_bank_json TEXT NOT NULL,
          current_music TEXT,
          ambience_bank_json TEXT NOT NULL,
          sfx_bank_json TEXT NOT NULL,
          scene_order INTEGER NOT NULL DEFAULT 0,
          updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
          FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_assets (
          session_id TEXT NOT NULL,
          asset_id TEXT NOT NULL,
          preload TEXT NOT NULL DEFAULT 'warm',
          volume_db REAL NOT NULL DEFAULT 0.0,
          loop INTEGER NOT NULL DEFAULT 0,
          sort_order INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (session_id, asset_id),
          FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );
        """
    )

    try:
        conn.execute("ALTER TABLE scenes ADD COLUMN scene_order INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    # Normalize legacy scenes that all received the old default order of 0.
    legacy = conn.execute("SELECT id FROM scenes ORDER BY rowid").fetchall()
    if legacy:
        orders = conn.execute("SELECT scene_order FROM scenes").fetchall()
        if len({int(r[0]) for r in orders}) <= 1:
            for index, row in enumerate(legacy):
                conn.execute("UPDATE scenes SET scene_order=? WHERE id=?", (index, row[0]))
    conn.commit()
    conn.close()


def db_connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _clean_text(value: Any, field: str, *, max_length: int = 200) -> str:
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": field, "message": "Muss Text sein."})
    value = value.strip()
    if not value or len(value) > max_length:
        raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": field, "message": "Darf nicht leer sein und ist zu lang."})
    return value


def _json_list(value: Any, field: str) -> List[Any]:
    if not isinstance(value, list):
        raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": field, "message": "Muss eine Liste sein."})
    return value


def _finite_number(value: Any, field: str, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": field, "message": "Muss eine Zahl sein."})
    if not (-1000 <= number <= 1000):
        raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": field, "message": "Wert liegt außerhalb des erlaubten Bereichs."})
    return number


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _load_or_create_game_meta(game_folder: Path) -> Dict[str, Any]:
    """Ensure each game folder has a stable UUID-based id.

    Creates <game_folder>/.soundboard-game.json on first run.
    """
    meta_path = game_folder / ".soundboard-game.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            # If corrupted, fall through and recreate safely
            pass

    meta = {
        "id": uuid.uuid4().hex,
        "name": game_folder.name,
        "created_at": int(time.time()),
        "version": 1,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def _asset_id(game_id: str, bucket: str, rel_path: str) -> str:
    # Stable across renames of the *game folder name*, because it keys on UUID game_id.
    # Changes if the file's relative path changes (intentional; can be extended with aliasing later).
    base = f"{game_id}:{bucket}:{rel_path}".encode("utf-8")
    return uuid.uuid5(uuid.NAMESPACE_URL, base.decode("utf-8")).hex


def scan_assets(games_dir: Path) -> Tuple[List[Dict[str, Any]], List[Asset]]:
    """Scan games directory for assets.

    Returns:
      games: [{id, name}]
      assets: list[Asset]

    - game_id is a stable UUID stored in each game folder.
    - asset_id is UUIDv5 derived from (game_id, bucket, rel_path).
    """
    if not games_dir.exists():
        games_dir.mkdir(parents=True, exist_ok=True)

    games: List[Dict[str, Any]] = []
    assets: List[Asset] = []

    for game_folder in sorted([p for p in games_dir.iterdir() if p.is_dir()]):
        meta = _load_or_create_game_meta(game_folder)
        game_id = meta.get("id") or uuid.uuid4().hex
        game_name = meta.get("name") or game_folder.name
        games.append({"id": game_id, "name": game_name})

        for bucket in VALID_BUCKETS:
            bucket_dir = game_folder / bucket
            if not bucket_dir.exists():
                continue
            for f in sorted(bucket_dir.rglob("*")):
                if not f.is_file():
                    continue
                if f.suffix.lower() not in AUDIO_EXTS:
                    continue
                rel = f.relative_to(game_folder).as_posix()  # e.g. Musik/foo.ogg
                asset_id = _asset_id(game_id, bucket, rel)
                assets.append(
                    Asset(
                        id=asset_id,
                        game_id=game_id,
                        bucket=bucket,
                        filename=f.name,
                        rel_path=rel,
                        size=f.stat().st_size,
                    )
                )

    return games, assets


def make_app(
    games_dir: Path,
    db_path: Path,
    ui_dir: Path,
    language: str = "en",
    admin_token: Optional[str] = None,
    cors_origins: Optional[List[str]] = None,
    log_path: Optional[Path] = None,
    write_rate_limit: int = 60,
) -> FastAPI:
    init_db(db_path)
    language = language.strip().lower()
    supported_languages = {"en", "de"}
    if language not in supported_languages:
        raise ValueError(f"SOUNDBOARD_LANGUAGE must be one of: {', '.join(sorted(supported_languages))}")
    logger = configure_logging(log_path)
    limiter = SlidingWindowRateLimiter(limit=max(1, write_rate_limit), window_seconds=60)

    app = FastAPI(title="DnD Soundboard Server", version="0.3")

    origins = cors_origins if cors_origins is not None else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Token"],
    )

    @app.middleware("http")
    async def operational_guard(request: Request, call_next):
        if request.method in WRITE_PATHS and request.url.path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            if not limiter.allowed(client):
                logger.warning("rate_limit method=%s path=%s client=%s", request.method, request.url.path, client)
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=429, content={"detail": {"code": "rate_limited", "message": "Zu viele Schreibvorgänge. Bitte später erneut versuchen."}})
        response = await call_next(request)
        if request.method in WRITE_PATHS and request.url.path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            logger.info("audit method=%s path=%s status=%s client=%s", request.method, request.url.path, response.status_code, client)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/api/health")
    def health() -> Dict[str, Any]:
        db_ok = False
        try:
            conn = db_connect(db_path)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            db_ok = True
        except sqlite3.Error as exc:
            logger.exception("health database_check_failed: %s", exc)
        games, assets = _get_scanned()
        return {
            "ok": db_ok,
            "database": "ok" if db_ok else "error",
            "games": len(games),
            "assets": len(assets),
            "scan_cache_age_seconds": round(max(0.0, time.time() - _asset_cache["ts"]), 3),
        }

    @app.get("/api/games")
    def list_games() -> Dict[str, Any]:
        games, _ = _get_scanned()
        return {"games": games}

    @app.post("/api/games")
    def create_game(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        name = _clean_text(payload.get("name"), "name", max_length=100)
        if name in {".", ".."} or any(ch in name for ch in "\\\\/\x00"):
            raise HTTPException(status_code=422, detail={"code": "invalid_name", "field": "name", "message": "Invalid game name."})
        if name.strip(" .") != name or not name.strip():
            raise HTTPException(status_code=422, detail={"code": "invalid_name", "field": "name", "message": "Game name cannot start or end with a space or dot."})
        game_folder = games_dir / name
        if game_folder.exists():
            raise HTTPException(status_code=409, detail={"code": "game_exists", "field": "name", "message": "A game with this name already exists."})
        try:
            game_folder.mkdir(parents=True, exist_ok=False)
            for bucket in sorted(VALID_BUCKETS):
                (game_folder / bucket).mkdir()
            meta = _load_or_create_game_meta(game_folder)
        except OSError as exc:
            raise HTTPException(status_code=500, detail={"code": "game_create_failed", "message": str(exc)})
        _asset_cache["ts"] = 0.0
        return {"game": {"id": meta["id"], "name": meta["name"]}}

    def _require_admin(request):
        if not admin_token:
            return
        provided = request.headers.get("x-admin-token")
        if provided != admin_token:
            raise HTTPException(status_code=401, detail="Unauthorized")

    # simple in-memory cache for scans (per process)
    _asset_cache: Dict[str, Any] = {"ts": 0.0, "games": [], "assets": []}

    def _get_scanned() -> Tuple[List[Dict[str, Any]], List[Asset]]:
        now = time.time()
        if (now - _asset_cache["ts"]) < 2.0:
            return _asset_cache["games"], _asset_cache["assets"]
        games, assets = scan_assets(games_dir)
        valid_game_ids = {game["id"] for game in games}
        conn = db_connect(db_path)
        try:
            if valid_game_ids:
                placeholders = ",".join("?" for _ in valid_game_ids)
                conn.execute(f"DELETE FROM scenes WHERE game_id NOT IN ({placeholders})", tuple(valid_game_ids))
            else:
                conn.execute("DELETE FROM scenes")
            conn.commit()
        finally:
            conn.close()
        _asset_cache.update({"ts": now, "games": games, "assets": assets})
        return games, assets

    def _asset_map() -> Dict[str, Asset]:
        _, assets = _get_scanned()
        return {a.id: a for a in assets}

    def _require_game(game_id: Any) -> Dict[str, Any]:
        game_id = _clean_text(game_id, "game_id", max_length=100)
        games, _ = _get_scanned()
        game = next((g for g in games if g["id"] == game_id), None)
        if not game:
            raise HTTPException(status_code=404, detail={"code": "unknown_game", "message": "Spiel nicht gefunden."})
        return game

    def _require_session(conn: sqlite3.Connection, session_id: Any, game_id: Optional[str] = None) -> sqlite3.Row:
        session_id = _clean_text(session_id, "session_id", max_length=100)
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail={"code": "unknown_session", "message": "Session nicht gefunden."})
        if game_id is not None and row["game_id"] != game_id:
            raise HTTPException(status_code=409, detail={"code": "session_game_mismatch", "message": "Session gehört zu einem anderen Spiel."})
        return row

    def _validate_asset_ids(asset_ids: List[Any], game_id: str, *, field: str, expected_bucket: Optional[str] = None) -> List[str]:
        asset_map = _asset_map()
        result = []
        for raw_id in asset_ids:
            asset_id = _clean_text(raw_id, field, max_length=100)
            asset = asset_map.get(asset_id)
            if not asset:
                raise HTTPException(status_code=422, detail={"code": "unknown_asset", "field": field, "asset_id": asset_id, "message": "Asset nicht gefunden."})
            if asset.game_id != game_id:
                raise HTTPException(status_code=409, detail={"code": "asset_game_mismatch", "field": field, "asset_id": asset_id, "message": "Asset gehört zu einem anderen Spiel."})
            if expected_bucket and asset.bucket != expected_bucket:
                raise HTTPException(status_code=422, detail={"code": "asset_bucket_mismatch", "field": field, "asset_id": asset_id, "message": f"Asset muss aus dem Bereich {expected_bucket} stammen."})
            result.append(asset_id)
        return result

    def _require_session_asset_ids(conn: sqlite3.Connection, session_id: Optional[str], asset_ids: List[str]) -> None:
        if not session_id:
            return
        if not asset_ids:
            return
        placeholders = ",".join("?" for _ in asset_ids)
        rows = conn.execute(
            f"SELECT asset_id FROM session_assets WHERE session_id = ? AND asset_id IN ({placeholders})",
            (session_id, *asset_ids),
        ).fetchall()
        present = {r[0] for r in rows}
        missing = [asset_id for asset_id in asset_ids if asset_id not in present]
        if missing:
            raise HTTPException(status_code=409, detail={"code": "asset_not_in_session", "asset_ids": missing, "message": "Mindestens ein Asset ist nicht Teil der Session."})

    @app.get("/api/library")
    def get_library(game_id: str = Query(...), session_id: Optional[str] = Query(None)) -> Dict[str, Any]:
        game = _require_game(game_id)
        game_id = game["id"]

        allowed_asset_ids: Optional[set[str]] = None
        if session_id:
            conn = db_connect(db_path)
            session = _require_session(conn, session_id, game_id)
            rows = conn.execute(
                "SELECT asset_id FROM session_assets WHERE session_id = ?", (session["id"],)
            ).fetchall()
            conn.close()
            allowed_asset_ids = {r[0] for r in rows}
        _, assets = _get_scanned()

        by_bucket: Dict[str, List[Dict[str, Any]]] = {"Musik": [], "Ambience": [], "SFX": []}
        for a in assets:
            if a.game_id != game_id:
                continue
            if allowed_asset_ids is not None and a.id not in allowed_asset_ids:
                continue
            by_bucket[a.bucket].append(
                {
                    "id": a.id,
                    "bucket": a.bucket,
                    "filename": a.filename,
                    "rel_path": a.rel_path,
                    "size": a.size,
                    "stream_url": f"/api/stream/{game_id}/{a.bucket}/" + a.rel_path.split("/", 1)[1],
                }
            )

        return {"game_id": game_id, "library": by_bucket, "session_id": session_id}

    def scene_row_to_dict(r: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": r["id"],
            "game_id": r["game_id"],
            "session_id": r["session_id"],
            "title": r["title"],
            "group": r["scene_group"],
            "tags": json.loads(r["tags_json"]),
            "musicBank": json.loads(r["music_bank_json"]),
            "currentMusic": r["current_music"],
            "ambienceBank": json.loads(r["ambience_bank_json"]),
            "sfxBank": json.loads(r["sfx_bank_json"]),
            "order": r["scene_order"] if "scene_order" in r.keys() else 0,
            "updated_at": r["updated_at"],
        }

    @app.get("/api/scenes")
    def list_scenes(game_id: str = Query(...), session_id: Optional[str] = Query(None)) -> Dict[str, Any]:
        game = _require_game(game_id)
        game_id = game["id"]
        conn = db_connect(db_path)
        if session_id:
            session = _require_session(conn, session_id, game_id)
            rows = conn.execute(
                "SELECT * FROM scenes WHERE game_id = ? AND session_id = ? ORDER BY scene_order, scene_group, title",
                (game_id, session["id"]),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scenes WHERE game_id = ? ORDER BY scene_order, scene_group, title", (game_id,)
            ).fetchall()
        conn.close()
        return {"scenes": [scene_row_to_dict(r) for r in rows]}

    @app.post("/api/scenes")
    def upsert_scene(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        required = ["id", "game_id", "title", "group", "tags", "musicBank", "ambienceBank", "sfxBank"]
        for k in required:
            if k not in payload:
                raise HTTPException(status_code=400, detail=f"Missing field: {k}")

        scene_id = _clean_text(payload["id"], "id", max_length=100)
        game = _require_game(payload["game_id"])
        game_id = game["id"]
        title = _clean_text(payload["title"], "title")
        group = _clean_text(payload["group"], "group")
        tags = _json_list(payload["tags"], "tags")
        music_bank = _validate_asset_ids(_json_list(payload["musicBank"], "musicBank"), game_id, field="musicBank", expected_bucket="Musik")
        ambience_bank = _json_list(payload["ambienceBank"], "ambienceBank")
        sfx_bank = _json_list(payload["sfxBank"], "sfxBank")
        for field, entries in (("ambienceBank", ambience_bank), ("sfxBank", sfx_bank)):
            if any(not isinstance(item, dict) or not item.get("assetId") for item in entries):
                raise HTTPException(status_code=422, detail={"code": "invalid_bank_entry", "field": field, "message": "Jeder Eintrag benötigt assetId."})
        ambience_ids = [item["assetId"] for item in ambience_bank]
        sfx_ids = [item["assetId"] for item in sfx_bank]
        _validate_asset_ids(ambience_ids, game_id, field="ambienceBank", expected_bucket="Ambience")
        _validate_asset_ids(sfx_ids, game_id, field="sfxBank", expected_bucket="SFX")
        current_music = payload.get("currentMusic")
        if current_music is not None:
            current_music = _clean_text(current_music, "currentMusic", max_length=100)
            if current_music not in music_bank:
                raise HTTPException(status_code=422, detail={"code": "invalid_current_music", "message": "currentMusic muss in musicBank enthalten sein."})

        session_id = payload.get("session_id")
        try:
            scene_order = int(payload.get("order", 0))
        except (TypeError, ValueError):
            scene_order = 0
        conn = db_connect(db_path)
        if session_id:
            _require_session(conn, session_id, game_id)
            _require_session_asset_ids(conn, session_id, music_bank + ambience_ids + sfx_ids)

        conn.execute(
            """
            INSERT INTO scenes (id, game_id, session_id, title, scene_group, tags_json, music_bank_json, current_music,
                                ambience_bank_json, sfx_bank_json, scene_order, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
            ON CONFLICT(id) DO UPDATE SET
              game_id=excluded.game_id,
              session_id=excluded.session_id,
              title=excluded.title,
              scene_group=excluded.scene_group,
              tags_json=excluded.tags_json,
              music_bank_json=excluded.music_bank_json,
              current_music=excluded.current_music,
              ambience_bank_json=excluded.ambience_bank_json,
              sfx_bank_json=excluded.sfx_bank_json,
              scene_order=excluded.scene_order,
              updated_at=strftime('%s','now')
            """,
            (
                scene_id,
                game_id,
                session_id,
                title,
                group,
                json.dumps(tags, ensure_ascii=False),
                json.dumps(music_bank, ensure_ascii=False),
                current_music,
                json.dumps(ambience_bank, ensure_ascii=False),
                json.dumps(sfx_bank, ensure_ascii=False),
                scene_order,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
        conn.close()
        return {"scene": scene_row_to_dict(row)}

    @app.patch("/api/scenes/{scene_id}/order")
    def reorder_scene(scene_id: str, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        try:
            scene_order = int(payload.get("order"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail={"code": "invalid_order", "message": "Order must be an integer."})
        conn = db_connect(db_path)
        row = conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Scene not found")
        conn.execute("UPDATE scenes SET scene_order=?, updated_at=strftime('%s','now') WHERE id=?", (scene_order, scene_id))
        conn.commit()
        row = conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone()
        conn.close()
        return {"scene": scene_row_to_dict(row)}

    @app.delete("/api/scenes/{scene_id}")
    def delete_scene(scene_id: str, request: Request) -> Dict[str, Any]:
        _require_admin(request)
        conn = db_connect(db_path)
        conn.execute("DELETE FROM scenes WHERE id=?", (scene_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    # ---------------------- Sessions (Packs) ----------------------

    @app.get("/api/sessions")
    def list_sessions(game_id: str = Query(...)) -> Dict[str, Any]:
        game = _require_game(game_id)
        conn = db_connect(db_path)
        rows = conn.execute(
            "SELECT id, game_id, title, created_at, updated_at FROM sessions WHERE game_id = ? ORDER BY updated_at DESC",
            (game_id,),
        ).fetchall()
        conn.close()
        return {"sessions": [dict(r) for r in rows]}

    @app.post("/api/sessions")
    def create_session(payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        if "game_id" not in payload or "title" not in payload:
            raise HTTPException(status_code=400, detail={"code": "missing_field", "message": "game_id und title sind erforderlich."})
        game = _require_game(payload["game_id"])
        title = _clean_text(payload["title"], "title")
        sid = payload.get("id") or uuid.uuid4().hex
        sid = _clean_text(sid, "id", max_length=100)
        conn = db_connect(db_path)
        conn.execute(
            "INSERT INTO sessions (id, game_id, title, created_at, updated_at) VALUES (?, ?, ?, strftime('%s','now'), strftime('%s','now'))",
            (sid, game["id"], title),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        conn.close()
        return {"session": dict(row)}

    @app.patch("/api/sessions/{session_id}")
    def rename_session(session_id: str, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        title = _clean_text(payload.get("title"), "title")
        conn = db_connect(db_path)
        _require_session(conn, session_id)
        conn.execute("UPDATE sessions SET title = ?, updated_at = strftime('%s','now') WHERE id = ?", (title, session_id))
        conn.commit()
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        conn.close()
        return {"session": dict(row)}

    @app.post("/api/sessions/{session_id}/duplicate")
    def duplicate_session(session_id: str, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        conn = db_connect(db_path)
        source = _require_session(conn, session_id)
        title = _clean_text(payload.get("title") or f"{source['title']} – Kopie", "title")
        new_id = uuid.uuid4().hex
        try:
            conn.execute("BEGIN")
            conn.execute(
                "INSERT INTO sessions (id, game_id, title) VALUES (?, ?, ?)",
                (new_id, source["game_id"], title),
            )
            conn.execute("""
                INSERT INTO session_assets (session_id, asset_id, preload, volume_db, loop, sort_order)
                SELECT ?, asset_id, preload, volume_db, loop, sort_order
                FROM session_assets WHERE session_id = ?
            """, (new_id, session_id))
            rows = conn.execute("SELECT * FROM scenes WHERE session_id = ?", (session_id,)).fetchall()
            for scene in rows:
                conn.execute("""
                    INSERT INTO scenes (id, game_id, session_id, title, scene_group, tags_json, music_bank_json,
                                        current_music, ambience_bank_json, sfx_bank_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
                """, (
                    uuid.uuid4().hex, scene["game_id"], new_id, scene["title"], scene["scene_group"],
                    scene["tags_json"], scene["music_bank_json"], scene["current_music"],
                    scene["ambience_bank_json"], scene["sfx_bank_json"],
                ))
            conn.commit()
        except Exception:
            conn.rollback()
            conn.close()
            raise
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (new_id,)).fetchone()
        conn.close()
        return {"session": dict(row)}

    @app.delete("/api/sessions/{session_id}")
    def delete_session(session_id: str, request: Request) -> Dict[str, Any]:
        _require_admin(request)
        conn = db_connect(db_path)
        _require_session(conn, session_id)
        # Scenes are owned by the session. Delete them explicitly so this also
        # cleans up databases created with the older ON DELETE SET NULL schema.
        conn.execute("DELETE FROM scenes WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM session_assets WHERE session_id=?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    @app.get("/api/sessions/{session_id}/assets")
    def get_session_assets(session_id: str) -> Dict[str, Any]:
        conn = db_connect(db_path)
        session = _require_session(conn, session_id)
        rows = conn.execute(
            "SELECT asset_id, preload, volume_db, loop, sort_order FROM session_assets WHERE session_id = ? ORDER BY sort_order, asset_id",
            (session_id,),
        ).fetchall()
        conn.close()
        return {"assets": [dict(r) for r in rows]}

    @app.post("/api/sessions/{session_id}/assets")
    def upsert_session_assets(session_id: str, payload: Dict[str, Any], request: Request) -> Dict[str, Any]:
        _require_admin(request)
        items = payload.get("assets")
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="Missing field: assets (list)")

        conn = db_connect(db_path)
        session = _require_session(conn, session_id)
        _, assets = _get_scanned()
        asset_map = {a.id: a for a in assets}
        normalized = []
        for it in items:
            if not isinstance(it, dict):
                raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": "assets", "message": "Jedes Asset muss ein Objekt sein."})
            asset_id = _clean_text(it.get("asset_id"), "asset_id", max_length=100)
            asset = asset_map.get(asset_id)
            if not asset:
                raise HTTPException(status_code=422, detail={"code": "unknown_asset", "asset_id": asset_id, "message": "Asset nicht gefunden."})
            if asset.game_id != session["game_id"]:
                raise HTTPException(status_code=409, detail={"code": "asset_game_mismatch", "asset_id": asset_id, "message": "Asset gehört zu einem anderen Spiel."})
            preload = (it.get("preload") or "warm").lower()
            if preload not in {"hot", "warm", "cold"}:
                raise HTTPException(status_code=422, detail={"code": "invalid_preload", "asset_id": asset_id, "message": "Preload muss hot, warm oder cold sein."})
            volume_db = _finite_number(it.get("volume_db"), "volume_db")
            try:
                sort_order = int(it.get("sort_order") if it.get("sort_order") is not None else 0)
            except (TypeError, ValueError):
                raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": "sort_order", "message": "Muss eine Ganzzahl sein."})
            if sort_order < 0:
                raise HTTPException(status_code=422, detail={"code": "invalid_field", "field": "sort_order", "message": "Darf nicht negativ sein."})
            normalized.append((asset_id, preload, volume_db, 1 if it.get("loop") else 0, sort_order))
        for asset_id, preload, volume_db, loop, sort_order in normalized:
            conn.execute(
                """
                INSERT INTO session_assets (session_id, asset_id, preload, volume_db, loop, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, asset_id) DO UPDATE SET
                  preload=excluded.preload,
                  volume_db=excluded.volume_db,
                  loop=excluded.loop,
                  sort_order=excluded.sort_order
                """,
                (session_id, asset_id, preload, volume_db, loop, sort_order),
            )

        conn.execute("UPDATE sessions SET updated_at = strftime('%s','now') WHERE id=?", (session_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    @app.delete("/api/sessions/{session_id}/assets/{asset_id}")
    def remove_session_asset(session_id: str, asset_id: str, request: Request) -> Dict[str, Any]:
        _require_admin(request)
        conn = db_connect(db_path)
        _require_session(conn, session_id)
        asset_id = _clean_text(asset_id, "asset_id", max_length=100)
        conn.execute(
            "DELETE FROM session_assets WHERE session_id=? AND asset_id=?", (session_id, asset_id)
        )
        conn.execute("UPDATE sessions SET updated_at = strftime('%s','now') WHERE id=?", (session_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    def _find_game_folder_by_id(game_id: str) -> Optional[Path]:
        for p in games_dir.iterdir():
            if not p.is_dir():
                continue
            meta_path = p / ".soundboard-game.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if meta.get("id") == game_id:
                return p
        return None

    @app.get("/api/stream/{game_id}/{bucket}/{rel_path:path}")
    def stream_asset(game_id: str, bucket: str, rel_path: str):
        if bucket not in VALID_BUCKETS:
            logger.warning("stream_invalid_bucket game_id=%s bucket=%s", game_id, bucket)
            raise HTTPException(status_code=400, detail="Invalid bucket")

        game_folder = _find_game_folder_by_id(game_id)
        if not game_folder:
            raise HTTPException(status_code=404, detail="Unknown game")

        bucket_root = (game_folder / bucket).resolve()
        requested = (bucket_root / rel_path).resolve()
        try:
            requested.relative_to(bucket_root)
        except ValueError:
            logger.warning("stream_path_traversal game_id=%s bucket=%s rel_path=%s", game_id, bucket, rel_path)
            raise HTTPException(status_code=400, detail="Invalid path")
        if requested.suffix.lower() not in AUDIO_EXTS:
            logger.warning("stream_invalid_type game_id=%s bucket=%s rel_path=%s", game_id, bucket, rel_path)
            raise HTTPException(status_code=400, detail="Invalid audio type")
        if not requested.exists() or not requested.is_file():
            logger.info("stream_not_found game_id=%s bucket=%s rel_path=%s", game_id, bucket, rel_path)
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(requested)

    # UI hosting
    if ui_dir.exists():
        assets_dir = ui_dir / "assets"
        if assets_dir.exists() and assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        def render_index() -> str:
            index_file = ui_dir / "index.html"
            if not index_file.exists():
                raise HTTPException(status_code=500, detail="UI index.html missing")
            return index_file.read_text(encoding="utf-8").replace("{{LANGUAGE}}", language)

        @app.get("/language.json")
        def languages_json():
            language_file = ui_dir / "language.json"
            if not language_file.exists():
                language_file = Path(__file__).resolve().parent / "language.json"
            if not language_file.exists():
                raise HTTPException(status_code=404, detail="language.json missing")
            return FileResponse(language_file, media_type="application/json")

        @app.get("/", response_class=HTMLResponse)
        def index():
            return render_index()

        # SPA fallback
        @app.get("/{path:path}", response_class=HTMLResponse)
        def spa_fallback(path: str):
            return render_index()

    else:
        @app.get("/", response_class=HTMLResponse)
        def no_ui():
            return "<h1>Soundboard Server</h1><p>UI not built yet. Use the API under /api/*</p>"

    return app


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games-dir", default=os.environ.get("SOUNDBOARD_GAMES_DIR", "./library"), help="Root dir containing game folders")
    ap.add_argument("--db", default=os.environ.get("SOUNDBOARD_DB", "./soundboard.db"), help="SQLite DB file")
    ap.add_argument("--ui-dir", default=os.environ.get("SOUNDBOARD_UI_DIR", "./ui-dist"), help="Directory with built UI (index.html + assets/)")
    ap.add_argument("--host", default=os.environ.get("SOUNDBOARD_HOST", "0.0.0.0"))
    ap.add_argument("--port", default=int(os.environ.get("SOUNDBOARD_PORT", "8000")), type=int)
    ap.add_argument("--language", default=os.environ.get("SOUNDBOARD_LANGUAGE", "en"), choices=sorted({"en", "de"}), help="UI language")
    ap.add_argument("--admin-token", default=os.environ.get("SOUNDBOARD_ADMIN_TOKEN"), help="If set, require X-Admin-Token for write endpoints")
    ap.add_argument("--cors-origins", default=os.environ.get("SOUNDBOARD_CORS_ORIGINS", "*"), help="Comma-separated allowed CORS origins; use * only for development")
    ap.add_argument("--log-file", default=os.environ.get("SOUNDBOARD_LOG_FILE"), help="Rotating log file path")
    ap.add_argument("--write-rate-limit", default=int(os.environ.get("SOUNDBOARD_WRITE_RATE_LIMIT", "60")), type=int, help="Maximum API writes per client per minute")
    args = ap.parse_args()

    games_dir = Path(args.games_dir)
    db_path = Path(args.db)
    ui_dir = Path(args.ui_dir)
    cors_origins = [item.strip() for item in args.cors_origins.split(",") if item.strip()]
    if not cors_origins:
        cors_origins = ["*"]
    log_path = Path(args.log_file) if args.log_file else None

    ensure_parent(db_path)

    app = make_app(
        games_dir=games_dir,
        db_path=db_path,
        ui_dir=ui_dir,
        language=args.language,
        admin_token=args.admin_token,
        cors_origins=cors_origins,
        log_path=log_path,
        write_rate_limit=args.write_rate_limit,
    )

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
