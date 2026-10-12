#!/usr/bin/env python3
"""
Build the database writes that sync eTender Pro into the Ryno-Tec business hub.

The hub is a Claude artifact with a shared database. A scheduled Claude task:
  1. reads the hub's `tenders` collection into a folder (ArtifactData list with out_dir),
  2. runs this script,
  3. applies each batch it prints with ArtifactData action "batch".

Only open IT tenders with an online briefing are added. Tenders already in the hub are
refreshed (dates, briefing details, links) without touching the bid status or notes.

Usage:
    python3 tools/hub_sync.py data/tenders.json HUB_DIR [META_VERSION] > writes.json

HUB_DIR is the out_dir used for the ArtifactData read; documents are expected at
HUB_DIR/tenders/<doc_id>.json (the folder may be missing when the hub is empty).
Output: {"batches": [[write, ...], ...], "summary": {...}}, at most 50 writes per batch.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

SAST = timezone(timedelta(hours=2))
MODE = {"online": "Online", "online and in person": "Online and in person", "in person": "In person",
        "none": "No briefing", "unknown": "Not stated"}
FEED_FIELDS = ("title", "tenderNo", "buyer", "province", "category", "value", "closing", "briefing",
               "compulsory", "briefingAt", "briefingVenue", "briefingLink", "sourceUrl", "docsUrl", "ocid")


def local(value):
    """ISO timestamp -> 'YYYY-MM-DDTHH:MM' in South African time (the hub's datetime-local format)."""
    if not value:
        return ""
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if d.tzinfo is None:
        d = d.replace(tzinfo=SAST)
    return d.astimezone(SAST).strftime("%Y-%m-%dT%H:%M")


def url(value):
    value = str(value or "").strip()
    return value if re.match(r"^https?://", value, re.I) else ""


def to_hub(t):
    b = t.get("briefing") or {}
    docs = t.get("documents") or []
    return {
        "title": re.sub(r"\s+", " ", str(t.get("title") or t.get("reference") or "")).strip(),
        "tenderNo": str(t.get("reference") or ""),
        "buyer": str(t.get("department") or ""),
        "province": str(t.get("province") or ""),
        "category": str(t.get("category") or ""),
        "value": t.get("value") or None,
        "closing": local(t.get("closingDate")),
        "briefing": MODE.get(b.get("mode"), "Not stated"),
        "compulsory": b.get("compulsory") is True,
        "briefingAt": local(b.get("date")),
        "briefingVenue": str(b.get("venue") or b.get("note") or "")[:500],
        "briefingLink": url(b.get("link")),
        "sourceUrl": url(t.get("portalUrl")),
        "docsUrl": url(docs[0].get("url") if docs else ""),
        "ocid": str(t.get("id") or ""),
    }


def load_hub(hub_dir):
    folder = os.path.join(hub_dir, "tenders")
    docs = {}
    if not os.path.isdir(folder):
        return docs
    for name in os.listdir(folder):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            raw = json.load(f)
        # ArtifactData saves {id, version, data} or the bare document, depending on version
        data = raw.get("data") if isinstance(raw.get("data"), dict) else raw
        doc_id = raw.get("id") or raw.get("doc_id") or name[:-5]
        docs[doc_id] = {"version": raw.get("version"), "data": data}
    return docs


def main():
    feed_path, hub_dir = sys.argv[1], sys.argv[2]
    meta_version = sys.argv[3] if len(sys.argv) > 3 else ""  # version of meta/etender, if it exists
    with open(feed_path, encoding="utf-8") as f:
        feed = json.load(f)
    hub = load_hub(hub_dir)
    by_ocid = {d["data"].get("ocid"): (doc_id, d) for doc_id, d in hub.items() if d["data"].get("ocid")}

    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    writes, added, updated = [], 0, 0
    online = 0
    for t in feed.get("tenders", []):
        closing = t.get("closingDate")
        try:
            if closing and datetime.fromisoformat(closing.replace("Z", "+00:00")) < now:
                continue
        except ValueError:
            pass
        body = to_hub(t)
        is_online = bool((t.get("briefing") or {}).get("online"))
        online += is_online
        match = by_ocid.get(body["ocid"])
        if match:
            doc_id, doc = match
            old = doc["data"]
            change = {k: body[k] for k in FEED_FIELDS if old.get(k) != body[k]}
            if old.get("briefingLink") and not body["briefingLink"]:
                change.pop("briefingLink", None)  # keep a link the user pasted in
            if change:
                change["updatedAt"] = stamp
                entry = {"op": "update", "collection": "tenders", "doc_id": doc_id, "data": change}
                if doc.get("version"):
                    entry["if_version"] = doc["version"]
                writes.append(entry)
                updated += 1
        elif is_online and body["ocid"]:
            doc_id = re.sub(r"[^A-Za-z0-9_\-.~:@+]", "-", body["ocid"])[:200]
            writes.append({"op": "set", "collection": "tenders", "doc_id": doc_id,
                           "data": {**body, "status": "New", "notes": "", "createdAt": stamp, "updatedAt": stamp}})
            added += 1

    summary = {"syncedAt": stamp, "feedGeneratedAt": feed.get("generatedAt"), "online": online,
               "added": added, "updated": updated, "source": "https://kagiso933.github.io/etender-pro/"}
    batches = [writes[i:i + 49] for i in range(0, len(writes), 49)] or [[]]
    # the sync status shown on the hub's Tenders page goes in the last batch
    batches[-1].append({"op": "set", "collection": "meta", "doc_id": "etender", "data": summary,
                        **({"if_version": int(meta_version)} if meta_version else {})})
    json.dump({"batches": batches, "summary": summary}, sys.stdout, indent=1)
    print(f"\n{added} to add, {updated} to update, {online} open online-briefing tenders in the feed", file=sys.stderr)


if __name__ == "__main__":
    main()
