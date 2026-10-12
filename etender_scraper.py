#!/usr/bin/env python3
"""
SA eTender Pro - tender fetcher.

Pulls tenders from National Treasury's official eTenders open-data API
(Open Contracting Data Standard), keeps the ones that are still open and
IT-related, and writes them to data/tenders.json for the web app.

API docs: https://ocds-api.etenders.gov.za/swagger/index.html
Uses only the Python standard library, so it runs anywhere with Python 3.8+.

Usage:
    python3 etender_scraper.py                 # last 60 days of releases
    python3 etender_scraper.py --days 90 --out data/tenders.json
    python3 etender_scraper.py --all           # keep non-IT tenders too
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API_URL = "https://ocds-api.etenders.gov.za/api/OCDSReleases"
PORTAL_URL = "https://www.etenders.gov.za"
PAGE_SIZE = 50        # normal page size
SUB_PAGE_SIZE = 5     # used to step around records the API cannot serialise (HTTP 500)
WINDOW_DAYS = 1       # one day per query: the API slows down/500s on long date ranges

# Category -> keyword patterns (matched case-insensitively against title + description)
CATEGORIES = [
    ("Cybersecurity", [r"cyber", r"\bsecurity operations\b", r"\bSOC\b", r"firewall", r"penetration test",
                       r"vulnerability", r"\bSIEM\b", r"endpoint (detection|protection)", r"antivirus", r"anti-virus",
                       r"information security", r"\bISMS\b"]),
    ("Cloud Services", [r"\bcloud\b", r"\bazure\b", r"\bAWS\b", r"\bSaaS\b", r"\bIaaS\b", r"\bPaaS\b",
                        r"microsoft 365", r"office 365", r"\bM365\b", r"\bO365\b", r"hosting"]),
    ("Software & Systems", [r"software", r"\bERP\b", r"\bCRM\b", r"\bSAP\b", r"oracle", r"application development",
                            r"web(site| portal| application)", r"\bportal\b", r"system development",
                            r"management system", r"\blicen[cs]e", r"\bdatabase\b", r"mobile app", r"\bapp\b",
                            r"business intelligence", r"\bBI\b", r"data analytics", r"\bGIS\b", r"digiti[sz]",
                            r"\bAI\b", r"artificial intelligence", r"automation"]),
    ("Network & Infrastructure", [r"network", r"\bLAN\b", r"\bWAN\b", r"\bWi-?Fi\b", r"wireless", r"router",
                                  r"switch(es)?\b", r"server", r"data cent(re|er)", r"data storage", r"storage (array|solution|area network)", r"\bSAN\b",
                                  r"structured cabling", r"fibre", r"fiber", r"connectivity", r"internet",
                                  r"\bVPN\b", r"backup", r"disaster recovery", r"virtuali[sz]"]),
    ("End-User Computing", [r"laptop", r"desktop", r"computer", r"\bPCs?\b", r"tablet", r"printer", r"printing solution",
                            r"\b(computer|LCD|LED|desktop|PC) monitors?\b", r"end.user", r"\bEUC\b", r"peripheral"]),
    ("Telecoms & Unified Comms", [r"telecom", r"telephon", r"\bPABX\b", r"\bVoIP\b", r"unified communication",
                                  r"video conferenc", r"\bcellular\b", r"mobile (data|devices)", r"\bAPN\b"]),
    ("IT Services & Support", [r"\bICT\b", r"\bIT\b", r"information technology", r"information and communication technolog",
                               r"help ?desk", r"service desk", r"managed services?", r"technical support",
                               r"IT support", r"maintenance and support of", r"\bSLA\b"]),
]

# Phrases that look like IT but usually are not (reduce false positives)
EXCLUDE = [r"\bsecurity guard", r"\bguarding\b", r"physical security", r"security services? at",
           r"armed response", r"\bCCTV\b(?!.*network)", r"switchgear", r"water (tank|storage)", r"\bJoJo\b", r"gas monitor", r"\bswitch(es)? and sockets\b",
           r"water network", r"sewer network", r"road network", r"electrical network", r"reticulation"]

def _flags(pattern):
    """All-caps acronyms (IT, AI, SOC, LAN...) match case-sensitively so 'it'/'ai' don't count."""
    letters = re.sub(r"\\[a-zA-Z]|[^a-zA-Z]", "", pattern)
    return 0 if letters and letters.isupper() else re.I


_compiled = [(name, [re.compile(p, _flags(p)) for p in pats]) for name, pats in CATEGORIES]
_exclude = [re.compile(p, re.I) for p in EXCLUDE]


def classify(text):
    """Return (category, matched_terms) for IT tenders, or (None, []) if not IT."""
    hits = {}
    for name, patterns in _compiled:
        for rx in patterns:
            m = rx.search(text)
            if m:
                hits.setdefault(name, []).append(m.group(0))
    if not hits:
        return None, []
    strong = sum(len(v) for v in hits.values())
    # A single weak match next to a known false-positive phrase is not IT
    if strong <= 1 and any(rx.search(text) for rx in _exclude):
        return None, []
    best = max(hits.items(), key=lambda kv: len(kv[1]))
    return best[0], sorted({t.lower() for v in hits.values() for t in v})


STATS = {"requests": 0, "failed": 0, "seconds": 0.0}
DEADLINE = [None]  # monotonic time after which no new requests are started


class OutOfTime(Exception):
    pass


def gh_error(msg):
    """Print an error that also shows up as a GitHub Actions annotation."""
    print(f"::error::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"ERROR: {msg}", file=sys.stderr)


def fetch_page(page, date_from, date_to, page_size=PAGE_SIZE, retries=3):
    params = urllib.parse.urlencode({
        "PageNumber": page, "PageSize": page_size,
        "dateFrom": date_from, "dateTo": date_to,
    })
    req = urllib.request.Request(f"{API_URL}?{params}", headers={
        "Accept": "application/json",
        "User-Agent": "SA-eTender-Pro/1.0 (+https://github.com/Kagiso933/etender-pro)",
    })
    for attempt in range(1, retries + 1):
        if DEADLINE[0] and time.monotonic() > DEADLINE[0]:
            raise OutOfTime()
        t0 = time.monotonic()
        STATS["requests"] += 1
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                out = json.loads(resp.read().decode("utf-8"))
                STATS["seconds"] += time.monotonic() - t0
                return out
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300].replace("\n", " ")
            detail = f"HTTP {e.code} {e.reason}: {body}"
        except Exception as e:  # timeout, DNS, connection reset, bad JSON
            detail = f"{type(e).__name__}: {e}"
        STATS["failed"] += 1
        STATS["seconds"] += time.monotonic() - t0
        print(f"  {date_from}..{date_to} page {page} (size {page_size}) attempt {attempt} failed - {detail}", file=sys.stderr)
        if attempt == retries:
            raise RuntimeError(f"eTenders API {date_from}..{date_to} page {page} failed after {retries} attempts - {detail}")
        time.sleep(5 * attempt)


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def to_tender(release, now, keep_all=False):
    t = release.get("tender") or {}
    end = parse_date((t.get("tenderPeriod") or {}).get("endDate"))
    if not end or end < now:
        return None  # closed or no closing date

    title = (t.get("title") or "").strip()
    description = (t.get("description") or "").strip()
    category, terms = classify(f"{title} {description}")
    if not category and not keep_all:
        return None

    value = t.get("value") or {}
    amount = value.get("amount") or 0
    buyer = (release.get("buyer") or {}).get("name") or (t.get("procuringEntity") or {}).get("name") or ""

    # Contact details live in the parties list when published
    contact = {}
    for party in release.get("parties") or []:
        cp = party.get("contactPoint") or {}
        if any(cp.get(k) for k in ("name", "email", "telephone")):
            contact = {k: cp.get(k) for k in ("name", "email", "telephone") if cp.get(k)}
            addr = party.get("address") or {}
            if addr.get("region"):
                contact["region"] = addr["region"]
            break

    docs = [{
        "title": d.get("title") or d.get("description") or "Document",
        "url": d.get("url"),
        "format": d.get("format"),
        "published": d.get("datePublished"),
    } for d in (t.get("documents") or []) if d.get("url")]

    start = parse_date((t.get("tenderPeriod") or {}).get("startDate"))
    return {
        "id": release.get("ocid"),
        "reference": title,  # eTenders "title" is usually the bid number
        "title": description or title,
        "department": buyer,
        "category": category or "Other",
        "matchedTerms": terms,
        "value": amount if amount and amount > 0 else None,
        "currency": value.get("currency") or "ZAR",
        "publishedDate": start.isoformat() if start else release.get("date"),
        "closingDate": end.isoformat(),
        "procurementMethod": t.get("procurementMethodDetails") or t.get("procurementMethod") or "",
        "procurementCategory": t.get("mainProcurementCategory") or ", ".join(t.get("additionalProcurementCategories") or []),
        "eligibility": t.get("eligibilityCriteria") or "",
        "submission": t.get("submissionMethodDetails") or "",
        "contact": contact,
        "documents": docs,
        "portalUrl": PORTAL_URL,  # search the portal by the reference number
    }


def fetch_window(date_from, date_to, latest, gaps):
    """Page through one date window.

    Some releases make the API return HTTP 500 for any page that contains them.
    When a page fails, re-read that slice in pages of SUB_PAGE_SIZE and skip only
    the small pages that still fail, so one bad record costs at most a few tenders.
    """
    def keep(releases):
        for r in releases:
            ocid = r.get("ocid")
            if ocid and (ocid not in latest or (r.get("date") or "") >= (latest[ocid].get("date") or "")):
                latest[ocid] = r

    count = 0
    ratio = PAGE_SIZE // SUB_PAGE_SIZE
    for page in range(1, 1000):
        try:
            releases = fetch_page(page, date_from, date_to, PAGE_SIZE, retries=2).get("releases") or []
        except RuntimeError:
            ended = False
            for sub in range((page - 1) * ratio + 1, page * ratio + 1):
                try:
                    part = fetch_page(sub, date_from, date_to, SUB_PAGE_SIZE, retries=1).get("releases") or []
                except RuntimeError:
                    gaps.append(f"{date_from}..{date_to} records {(sub - 1) * SUB_PAGE_SIZE + 1}-{sub * SUB_PAGE_SIZE}")
                    continue
                keep(part)
                count += len(part)
                if len(part) < SUB_PAGE_SIZE:
                    ended = True
                    break
            if ended:
                return count
            continue
        keep(releases)
        count += len(releases)
        if len(releases) < PAGE_SIZE:
            return count
        time.sleep(0.3)  # be polite to the API
    return count


def collect(days, keep_all=False, budget_minutes=30):
    now = datetime.now(timezone.utc)
    DEADLINE[0] = time.monotonic() + budget_minutes * 60
    oldest = (now - timedelta(days=days)).date()
    print(f"Fetching eTenders releases {now.date()} back to {oldest}, newest first ({budget_minutes} min budget)")

    latest = {}  # ocid -> newest release (releases repeat when a tender is updated)
    scanned, failed, gaps = 0, [], []
    covered_to = None
    day = now.date()
    while day >= oldest:
        win_start = max(day - timedelta(days=WINDOW_DAYS - 1), oldest)
        try:
            n = fetch_window(win_start.isoformat(), day.isoformat(), latest, gaps)
            scanned += n
            covered_to = win_start
            print(f"  {win_start}..{day}: {n} releases")
        except OutOfTime:
            print(f"::warning::Time budget reached - covered tenders published back to {covered_to}, not {oldest}", file=sys.stderr)
            break
        except RuntimeError as e:
            failed.append(str(e))
            print(f"  {win_start}..{day}: FAILED", file=sys.stderr)
        day = win_start - timedelta(days=1)

    if not latest:
        raise RuntimeError("; ".join(failed[:3]) or "no releases returned")
    for msg in failed[:5]:
        gh_error(f"Skipped a date window: {msg}")
    if gaps:
        print(f"::warning::Skipped {len(gaps)} small page(s) the API could not return (about {len(gaps) * SUB_PAGE_SIZE} records): "
              + "; ".join(gaps[:8]), file=sys.stderr)
    avg = STATS["seconds"] / max(1, STATS["requests"])
    print(f"::notice::{STATS['requests']} API requests ({STATS['failed']} failed, avg {avg:.1f}s); "
          f"{scanned} releases scanned; coverage {covered_to}..{now.date()}", file=sys.stderr)

    tenders = [x for x in (to_tender(r, now, keep_all) for r in latest.values()) if x]
    tenders.sort(key=lambda x: x["closingDate"])
    return tenders, scanned, len(latest), (covered_to.isoformat() if covered_to else None)


def main():
    ap = argparse.ArgumentParser(description="Fetch open IT tenders from the eTenders OCDS API")
    ap.add_argument("--days", type=int, default=60, help="how far back to look for published tenders")
    ap.add_argument("--out", default="data/tenders.json")
    ap.add_argument("--all", action="store_true", help="keep non-IT tenders too")
    ap.add_argument("--budget", type=float, default=30, help="stop fetching after this many minutes and save what we have")
    args = ap.parse_args()

    try:
        tenders, scanned, unique, covered_from = collect(args.days, keep_all=args.all, budget_minutes=args.budget)
    except Exception as e:
        gh_error(str(e))
        sys.exit(1)
    cats = {}
    for t in tenders:
        cats[t["category"]] = cats.get(t["category"], 0) + 1

    payload = {
        "source": API_URL,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "lookbackDays": args.days,
        "coveredFrom": covered_from,
        "releasesScanned": scanned,
        "uniqueTenders": unique,
        "count": len(tenders),
        "categories": cats,
        "tenders": tenders,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    print(f"\nScanned {scanned} releases ({unique} unique tenders)")
    print(f"Open IT tenders: {len(tenders)} -> {args.out}")
    for name, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()
