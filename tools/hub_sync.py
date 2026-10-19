#!/usr/bin/env python3
"""
Build the database writes that sync eTender Pro into the Ryno-Tec business hub.

The hub is a Claude artifact with a shared database. A scheduled Claude task:
  1. reads the hub's `tenders` collection into a folder (ArtifactData list with out_dir),
  2. runs this script,
  3. applies each batch it prints with ArtifactData action "batch".

Two companies share the hub, and each tender document carries a "company" field:
  - Ryno-Tec ("rtc"): open IT tenders with an online briefing, from data/tenders.json.
  - Lesego Laka Projects ("llp"): open maintenance, grounds, agriculture and supply tenders
    in Gauteng, from data/tenders-llp.json beside the IT feed (read automatically if present).
Tenders already in the hub are refreshed (dates, briefing details, links) without touching
the bid status or notes.

Usage:
    python3 tools/hub_sync.py data/tenders.json HUB_DIR [META_VERSION] [VERSIONS_JSON] > writes.json

META_VERSION is meta/etender's version ("" when that doc doesn't exist yet). VERSIONS_JSON is a
file mapping each existing tenders doc_id to the version shown in the ArtifactData list result;
writes to existing documents need it.

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
GAUTENG = re.compile(r"gauteng|tshwane|pretoria|johannesburg|joburg|soweto|ekurhuleni|germiston|benoni|boksburg|"
                     r"kempton|tembisa|springs|sedibeng|vereeniging|vanderbijlpark|emfuleni|midvaal|meyerton|lesedi|heidelberg|"
                     r"west rand|mogale|krugersdorp|randfontein|rand west|merafong|carletonville|westonaria|mabopane|"
                     r"soshanguve|ga-?rankuwa|hammanskraal|centurion|midrand|sandton|roodepoort|alberton", re.I)
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


def load_hub(hub_dir, versions):
    folder = os.path.join(hub_dir, "tenders")
    docs = {}
    if not os.path.isdir(folder):
        return docs
    for name in os.listdir(folder):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            raw = json.load(f)
        # ArtifactData out_dir saves the bare document as <doc_id>.json; versions come from VERSIONS_JSON
        wrapped = isinstance(raw.get("data"), dict) and "version" in raw
        data = raw["data"] if wrapped else raw
        doc_id = (raw.get("id") if wrapped else None) or name[:-5]
        docs[doc_id] = {"version": raw.get("version") if wrapped else versions.get(doc_id), "data": data}
    return docs


def in_gauteng(t):
    """Lesego Laka bids in Gauteng: match the province or any Gauteng place in the tender."""
    b, c = t.get("briefing") or {}, t.get("contact") or {}
    text = " ".join(str(x or "") for x in (t.get("province"), c.get("region"), t.get("department"), t.get("title"),
                                            t.get("eligibility"), t.get("submission"), b.get("venue"), b.get("note")))
    return bool(GAUTENG.search(text))


def main():
    feed_path, hub_dir = sys.argv[1], sys.argv[2]
    meta_version = sys.argv[3] if len(sys.argv) > 3 else ""  # version of meta/etender, if it exists ("" if not)
    versions = {}
    if len(sys.argv) > 4:  # JSON file {"<doc_id>": <version>, ...} copied from the ArtifactData list result
        with open(sys.argv[4], encoding="utf-8") as f:
            versions = {k: int(v) for k, v in json.load(f).items()}
    with open(feed_path, encoding="utf-8") as f:
        feed = json.load(f)
    llp_path = os.path.join(os.path.dirname(feed_path) or ".", "tenders-llp.json")
    llp_feed = {}
    if os.path.exists(llp_path):
        with open(llp_path, encoding="utf-8") as f:
            llp_feed = json.load(f)
    hub = load_hub(hub_dir, versions)
    missing = [d for d, v in hub.items() if not v["version"]]
    if missing:
        sys.exit(f"No version for existing hub documents {missing[:5]}: pass VERSIONS_JSON with every listed doc's version")
    by_ocid = {d["data"].get("ocid"): (doc_id, d) for doc_id, d in hub.items() if d["data"].get("ocid")}

    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    writes, added, updated = [], 0, 0
    online = 0
    llp = {"open": 0, "added": 0, "updated": 0, "outsideGauteng": 0}
    items = [("rtc", t) for t in feed.get("tenders", [])] + [("llp", t) for t in llp_feed.get("tenders", [])]
    for company, t in items:
        closing = t.get("closingDate")
        try:
            if closing and datetime.fromisoformat(closing.replace("Z", "+00:00")) < now:
                continue
        except ValueError:
            pass
        body = to_hub(t)
        is_online = bool((t.get("briefing") or {}).get("online"))
        if company == "rtc":
            online += is_online
            wanted = is_online
        else:
            wanted = in_gauteng(t)
            llp["open" if wanted else "outsideGauteng"] += 1
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
                if company == "llp":
                    llp["updated"] += 1
                else:
                    updated += 1
        elif wanted and body["ocid"]:
            doc_id = re.sub(r"[^A-Za-z0-9_\-.~:@+]", "-", body["ocid"])[:200]
            writes.append({"op": "set", "collection": "tenders", "doc_id": doc_id,
                           "data": {**body, "company": company, "status": "New", "notes": "", "createdAt": stamp, "updatedAt": stamp}})
            if company == "llp":
                llp["added"] += 1
            else:
                added += 1

    summary = {"syncedAt": stamp, "feedGeneratedAt": feed.get("generatedAt"), "online": online,
               "added": added, "updated": updated, "source": "https://kagiso933.github.io/etender-pro/",
               "companies": {"llp": llp}}
    batches = [writes[i:i + 49] for i in range(0, len(writes), 49)] or [[]]
    # the sync status shown on the hub's Tenders page goes in the last batch
    batches[-1].append({"op": "set", "collection": "meta", "doc_id": "etender", "data": summary,
                        **({"if_version": int(meta_version)} if meta_version else {})})
    json.dump({"batches": batches, "summary": summary}, sys.stdout, indent=1)
    print(f"\nRyno-Tec: {added} to add, {updated} to update, {online} open online-briefing tenders in the feed", file=sys.stderr)
    print(f"Lesego Laka: {llp['added']} to add, {llp['updated']} to update, {llp['open']} open in Gauteng "
          f"({llp['outsideGauteng']} elsewhere skipped)", file=sys.stderr)


if __name__ == "__main__":
    main()
