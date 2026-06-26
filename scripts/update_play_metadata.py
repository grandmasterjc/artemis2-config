"""Update Google Play Store listing metadata for Artemis Tracker.

Reads play_metadata.json from repo root with:
  package_name, default_language, listings (per locale: title, shortDescription, fullDescription),
  release_notes (per locale).

Modes:
  --show-current : print current listing + active draft, do nothing
  --dry-run      : build edit, stage changes, then ABORT (no commit)
  apply (default): build edit, stage changes, COMMIT

Requires env:
  GOOGLE_PLAY_SERVICE_ACCOUNT_JSON  (full JSON of service account key)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_FILE = REPO_ROOT / "play_metadata.json"
PLAY_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"


# ---------- auth ----------
def get_access_token() -> str:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    json_blob = os.environ.get("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
    if not json_blob:
        raise RuntimeError("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON missing")
    info = json.loads(json_blob)
    scopes = ["https://www.googleapis.com/auth/androidpublisher"]
    creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
    creds.refresh(Request())
    return creds.token


# ---------- http helpers ----------
def play_request(
    token: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
) -> dict:
    url = PLAY_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Play {method} {path} -> HTTP {e.code}\n{err_body}"
        ) from e


# ---------- edits API ----------
def create_edit(token: str, package: str) -> str:
    data = play_request(token, "POST", f"/applications/{package}/edits", body={})
    return data["id"]


def commit_edit(token: str, package: str, edit_id: str) -> dict:
    return play_request(token, "POST", f"/applications/{package}/edits/{edit_id}:commit")


def delete_edit(token: str, package: str, edit_id: str) -> None:
    try:
        play_request(token, "DELETE", f"/applications/{package}/edits/{edit_id}")
    except Exception as e:
        print(f"  (delete edit failed: {e})")


# ---------- listings ----------
def list_listings(token: str, package: str, edit_id: str) -> list[dict]:
    data = play_request(
        token, "GET", f"/applications/{package}/edits/{edit_id}/listings"
    )
    return data.get("listings", [])


def patch_listing(
    token: str,
    package: str,
    edit_id: str,
    language: str,
    listing: dict,
) -> dict:
    return play_request(
        token,
        "PUT",
        f"/applications/{package}/edits/{edit_id}/listings/{language}",
        body=listing,
    )


# ---------- tracks (release notes) ----------
def get_track(token: str, package: str, edit_id: str, track: str) -> dict:
    return play_request(
        token, "GET", f"/applications/{package}/edits/{edit_id}/tracks/{track}"
    )


def patch_track_release_notes(
    token: str,
    package: str,
    edit_id: str,
    track_name: str,
    release_notes: dict,
) -> dict:
    """Updates release notes on the latest release of the given track.

    release_notes is { locale: text }. Preserves existing track structure.
    """
    track = get_track(token, package, edit_id, track_name)
    releases = track.get("releases", [])
    if not releases:
        print(f"  Track {track_name} has no releases; cannot set notes here.")
        return track
    # Modify the latest release (status=draft preferred)
    target = releases[0]
    notes = [
        {"language": loc, "text": txt} for loc, txt in release_notes.items()
    ]
    target["releaseNotes"] = notes
    body = {"releases": releases, "track": track_name}
    return play_request(
        token,
        "PUT",
        f"/applications/{package}/edits/{edit_id}/tracks/{track_name}",
        body=body,
    )


# ---------- main ----------
def show_current(token: str, package: str) -> None:
    edit_id = create_edit(token, package)
    try:
        listings = list_listings(token, package, edit_id)
        print(f"=== {len(listings)} listings ===")
        for l in listings:
            lang = l.get("language")
            print(f"\n--- {lang} ---")
            print(f"  title: {l.get('title')}")
            print(f"  shortDescription: {l.get('shortDescription')}")
            full = l.get("fullDescription") or ""
            print(f"  fullDescription:\n{full}")
        # Show production track release notes
        for track_name in ("production", "internal"):
            try:
                track = get_track(token, package, edit_id, track_name)
                releases = track.get("releases", [])
                if releases:
                    print(f"\n--- track {track_name} latest release ---")
                    r = releases[0]
                    print(f"  name: {r.get('name')}")
                    print(f"  status: {r.get('status')}")
                    for note in r.get("releaseNotes", []):
                        print(f"  [{note['language']}]\n{note['text']}")
            except Exception as e:
                print(f"  (track {track_name}: {e})")
    finally:
        delete_edit(token, package, edit_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show-current", action="store_true")
    parser.add_argument(
        "--track", default="production",
        help="Track for release notes (production, internal, alpha, beta)",
    )
    args = parser.parse_args()

    if args.show_current and not METADATA_FILE.exists():
        # Allow show-current without metadata file; use default package
        package = os.environ.get("GOOGLE_PLAY_PACKAGE", "no.bitfactory.artemisii")
        token = get_access_token()
        print(f"Authenticated. Package: {package}")
        show_current(token, package)
        return 0

    if not METADATA_FILE.exists():
        print(f"ERROR: {METADATA_FILE} not found")
        return 1
    meta = json.loads(METADATA_FILE.read_text())
    package = meta["package_name"]

    token = get_access_token()
    print(f"Authenticated. Package: {package}")

    if args.show_current:
        show_current(token, package)
        return 0

    edit_id = create_edit(token, package)
    print(f"Edit created: {edit_id}")
    try:
        # Update listings
        for lang, fields in meta.get("listings", {}).items():
            print(f"  Patching listing {lang}")
            patch_listing(token, package, edit_id, lang, fields)

        # Update release notes on track if provided
        rn = meta.get("release_notes")
        if rn:
            print(f"  Patching release notes on track={args.track}")
            patch_track_release_notes(token, package, edit_id, args.track, rn)

        if args.dry_run:
            print("DRY RUN — deleting edit without commit")
            delete_edit(token, package, edit_id)
            return 0

        result = commit_edit(token, package, edit_id)
        print(f"Committed edit. id={result.get('id')}")
    except Exception:
        delete_edit(token, package, edit_id)
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
