"""Update App Store Connect metadata for Artemis Tracker.

Reads release notes, description, keywords, promotional text and version from
asc_metadata.json in the repo root, then PATCHes the matching draft
appStoreVersion in App Store Connect.

Required env (from GitHub Secrets):
  APP_STORE_CONNECT_KEY_ID
  APP_STORE_CONNECT_ISSUER_ID
  APP_STORE_CONNECT_PRIVATE_KEY

Usage:
  python scripts/update_asc_metadata.py
  python scripts/update_asc_metadata.py --dry-run

Workflow:
  1. Authenticate via JWT.
  2. Resolve app by bundle ID.
  3. Find or create draft appStoreVersion with target version_string.
  4. PATCH version-level fields (versionString).
  5. For each locale, PATCH appStoreVersionLocalizations:
       whatsNew, description, keywords, promotionalText.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_FILE = REPO_ROOT / "asc_metadata.json"
ASC_BASE = "https://api.appstoreconnect.apple.com/v1"


# ---------- auth ----------
def make_jwt(key_id: str, issuer_id: str, private_key_pem: str) -> str:
    import jwt  # PyJWT

    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 20 * 60,
        "aud": "appstoreconnect-v1",
    }
    headers = {"kid": key_id, "typ": "JWT"}
    return jwt.encode(payload, private_key_pem, algorithm="ES256", headers=headers)


# ---------- http helpers ----------
def asc_request(
    token: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
) -> dict:
    url = ASC_BASE + path
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
            f"ASC {method} {path} -> HTTP {e.code}\n{err_body}"
        ) from e


# ---------- app lookup ----------
def resolve_app_id(token: str, bundle_id: str) -> str:
    data = asc_request(
        token,
        "GET",
        "/apps",
        params={"filter[bundleId]": bundle_id, "limit": 1},
    )
    apps = data.get("data", [])
    if not apps:
        raise RuntimeError(f"No ASC app for bundle {bundle_id}")
    return apps[0]["id"]


def find_draft_version(token: str, app_id: str, version_string: str) -> dict | None:
    """Return the appStoreVersion dict matching version_string in an editable
    state, or None if not present."""
    data = asc_request(
        token,
        "GET",
        f"/apps/{app_id}/appStoreVersions",
        params={
            "filter[versionString]": version_string,
            "limit": 5,
        },
    )
    for v in data.get("data", []):
        state = v.get("attributes", {}).get("appStoreState", "")
        if state in {
            "PREPARE_FOR_SUBMISSION",
            "DEVELOPER_REJECTED",
            "REJECTED",
            "METADATA_REJECTED",
            "WAITING_FOR_REVIEW",
            "INVALID_BINARY",
        }:
            return v
        # Even READY_FOR_SALE / PROCESSING_FOR_APP_STORE -- return for visibility
        return v
    return None


def create_draft_version(
    token: str, app_id: str, version_string: str, platform: str = "IOS"
) -> dict:
    body = {
        "data": {
            "type": "appStoreVersions",
            "attributes": {
                "platform": platform,
                "versionString": version_string,
            },
            "relationships": {
                "app": {"data": {"type": "apps", "id": app_id}},
            },
        }
    }
    return asc_request(token, "POST", "/appStoreVersions", body=body)["data"]


# ---------- localization ----------
def list_localizations(token: str, version_id: str) -> list[dict]:
    data = asc_request(
        token,
        "GET",
        f"/appStoreVersions/{version_id}/appStoreVersionLocalizations",
        params={"limit": 50},
    )
    return data.get("data", [])


def patch_localization(
    token: str, loc_id: str, attributes: dict, dry_run: bool
) -> None:
    body = {
        "data": {
            "type": "appStoreVersionLocalizations",
            "id": loc_id,
            "attributes": attributes,
        }
    }
    if dry_run:
        print(f"  [DRY] PATCH /appStoreVersionLocalizations/{loc_id}")
        print(f"  [DRY] attrs: {list(attributes.keys())}")
        return
    asc_request(
        token, "PATCH", f"/appStoreVersionLocalizations/{loc_id}", body=body
    )


# ---------- main ----------
def list_all_versions(token: str, app_id: str, limit: int = 10) -> list[dict]:
    data = asc_request(
        token,
        "GET",
        f"/apps/{app_id}/appStoreVersions",
        params={"limit": limit, "sort": "-createdDate"},
    )
    return data.get("data", [])


def show_current(token: str, app_id: str) -> None:
    """Print recent versions and their en-US localization fields."""
    versions = list_all_versions(token, app_id, limit=10)
    print(f"=== {len(versions)} recent versions ===")
    for v in versions:
        attrs = v.get("attributes", {})
        vid = v["id"]
        vstr = attrs.get("versionString")
        state = attrs.get("appStoreState")
        created = attrs.get("createdDate")
        print(f"\n--- {vstr} (state={state}, created={created}, id={vid}) ---")
        locs = list_localizations(token, vid)
        for loc in locs:
            la = loc.get("attributes", {})
            if la.get("locale") != "en-US":
                continue
            print(f"  whatsNew:\n{la.get('whatsNew')}")
            print(f"  promotionalText: {la.get('promotionalText')}")
            print(f"  keywords: {la.get('keywords')}")
            desc = la.get('description') or ''
            print(f"  description (first 300): {desc[:300]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show-current", action="store_true",
                        help="Print recent versions and metadata, do not modify")
    args = parser.parse_args()

    if not METADATA_FILE.exists():
        print(f"ERROR: {METADATA_FILE} not found")
        return 1

    meta = json.loads(METADATA_FILE.read_text())
    bundle_id = meta["bundle_id"]
    version_string = meta["version"]
    locales = meta.get("locales", {})
    platform = meta.get("platform", "IOS")

    key_id = os.environ.get("APP_STORE_CONNECT_KEY_ID")
    issuer_id = os.environ.get("APP_STORE_CONNECT_ISSUER_ID")
    private_key = os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY")
    if not (key_id and issuer_id and private_key):
        print("ERROR: ASC credentials missing")
        return 1

    token = make_jwt(key_id, issuer_id, private_key)
    print(f"Resolving app for bundle {bundle_id} ...")
    app_id = resolve_app_id(token, bundle_id)
    print(f"  app_id={app_id}")

    if args.show_current:
        show_current(token, app_id)
        return 0

    version = find_draft_version(token, app_id, version_string)
    if version is None:
        print(f"No version {version_string} found.")
        if args.dry_run:
            print("[DRY] Would create new draft version.")
            return 0
        version = create_draft_version(token, app_id, version_string, platform)
        print(f"  Created version id={version['id']}")
    else:
        state = version.get("attributes", {}).get("appStoreState", "?")
        print(f"  Found version id={version['id']} state={state}")

    version_id = version["id"]

    # Patch the version itself if needed (e.g. release notes copy field)
    # whatsNew is per-locale, not per-version, so skip here.

    localizations = list_localizations(token, version_id)
    by_locale = {
        loc["attributes"]["locale"]: loc for loc in localizations
    }
    print(f"  Found {len(localizations)} localizations: {list(by_locale.keys())}")

    for locale_code, fields in locales.items():
        loc = by_locale.get(locale_code)
        if loc is None:
            print(f"  Locale {locale_code}: NOT FOUND in ASC, skipping")
            continue

        attrs = {}
        for key in (
            "description",
            "keywords",
            "promotionalText",
            "whatsNew",
            "marketingUrl",
            "supportUrl",
        ):
            if key in fields and fields[key] is not None:
                attrs[key] = fields[key]
        if not attrs:
            print(f"  Locale {locale_code}: no fields to patch")
            continue

        print(f"  Patching {locale_code}: {list(attrs.keys())}")
        patch_localization(token, loc["id"], attrs, args.dry_run)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
