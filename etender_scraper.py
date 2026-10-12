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

# Category -> keyword patterns (matched against title + description).
# Patterns starting with "~" are WEAK: common outside IT, so a tender needs at least one
# strong match, or two different weak matches, to count as IT.
CATEGORIES = [
    ("Cybersecurity", [r"privileged (remote )?access", r"e-?mail (security|archiv|filtering)", r"\b(mimecast|beyondtrust|fortinet|fortigate|sophos|kaspersky|eset|trend micro|crowdstrike|palo alto)\b", r"cyber", r"security operations cent(re|er)", r"firewall", r"penetration test",
                       r"vulnerability (assessment|scan|management)", r"\bSIEM\b", r"endpoint (detection|protection)",
                       r"anti-?virus", r"information security", r"\bISMS\b", r"\bPOPIA\b"]),
    ("Cloud Services", [r"cloud\s*-?\s*based", r"backup as a service", r"\bBaaS\b", r"\bveeam\b", r"\bazure\b", r"\bAWS\b", r"\bSaaS\b", r"\bIaaS\b", r"\bPaaS\b", r"microsoft 365",
                        r"office 365", r"\bM365\b", r"\bO365\b", r"cloud (computing|services?|migration|hosting|solution|platform|backup|storage|infrastructure)",
                        r"~\bcloud\b", r"~hosting"]),
    ("Software & Systems", [r"payroll (system|software|licen)", r"employee self.?servic", r"\bsage \d{3}", r"\bESS\b", r"\bmicrosoft\b", r"power ?bi\b", r"power platform", r"self.service portal", r"devops", r"development operations", r"\b(citrix|vmware|salesforce|servicenow|sage x3|sage 300|pastel)\b", r"~licen[cs]e renewal", r"software", r"\bERP\b", r"\bCRM\b", r"\bSAP\b", r"\boracle\b", r"application development",
                            r"web(site| portal| application| development)", r"system development", r"information (management )?system",
                            r"software licen[cs]", r"(microsoft|adobe|esri|autodesk|vmware|sage|pastel|arcgis|oracle|sap) .{0,40}licen[cs]",
                            r"mobile app", r"business intelligence", r"data analytics", r"\bGIS\b", r"artificial intelligence",
                            r"\bAI\b", r"learning management system", r"\bLMS\b", r"electronic (document|records|content) management",
                            r"~management system", r"~\bdatabase\b", r"~\bportal\b", r"~digiti[sz]", r"~automation",
                            r"~licen[cs]e", r"~\bapp\b", r"~\bsystem\b"]),
    ("Network & Infrastructure", [r"network monitoring", r"virtual environment", r"internet (access|links?|service provider|connectivity)", r"fib(re|er) termination", r"\b(cisco|huawei|aruba|juniper|mikrotik)\b", r"\bLAN\b", r"\bWAN\b", r"\bWi-?Fi\b", r"wireless (network|access)", r"router",
                                  r"network switch", r"server", r"data cent(re|er)", r"data storage",
                                  r"storage (array|solution|area network)", r"\bSAN\b", r"structured cabling",
                                  r"fib(re|er) optic", r"\bVPN\b", r"disaster recovery", r"virtuali[sz]", r"\bMPLS\b",
                                  r"(ICT|IT|computer|data|local area|wide area) network", r"network (infrastructure|equipment|security|upgrade|cabling)",
                                  r"~network", r"~connectivity", r"~internet", r"~backup", r"~\bswitch(es)?\b", r"~fib(re|er)"]),
    ("End-User Computing", [r"\bPC[\'’]?s\b", r"printers?\b", r"managed print", r"\bIT.related", r"\b(lenovo|dell|hp|hpe)\b (laptop|desktop|notebook|server|computer)", r"laptop", r"desktop", r"computers?\b", r"\bPCs\b", r"notebooks? computers?",
                            r"\b(computer|LCD|LED|desktop|PC) monitors?\b", r"end.user comput", r"\bEUC\b",
                            r"multifunction(al)? (printer|device)", r"~tablets?\b", r"~peripheral"]),
    ("Telecoms & Unified Comms", [r"communication network", r"satellite (airtime|communication)", r"telecommunication", r"telephony", r"\bPABX\b", r"\bVoIP\b", r"unified communication",
                                  r"video ?conferenc", r"~\bcellular\b", r"~mobile (data|devices)", r"\bAPN\b"]),
    ("IT Services & Support", [r"\bIT (internal )?audit", r"\bICT\b", r"information technology", r"information and communication technolog",
                               r"\bIT (services?|support|equipment|infrastructure|solutions?|systems?|hardware|security|governance|"
                               r"department|unit|helpdesk|help desk|professional|specialist|audit|strategy|managed)\b",
                               r"help ?desk", r"service desk", r"managed (IT |ICT )?services", r"desktop support",
                               r"~technical support", r"~\bSLA\b"]),
]

# Phrases that look like IT but usually are not; they cancel a lone weak match
EXCLUDE = [r"security guard", r"guarding", r"physical security", r"armed response", r"switchgear",
           r"water (tank|storage|meter|network|reticulation)", r"sewer", r"sanitation", r"road network",
           r"electrical network", r"reticulation", r"ceilometer", r"cloud (base|height|cover)", r"\bEPWP\b",
           r"liquor licen", r"business licen", r"driver'?s? licen", r"gas monitor", r"cleaning"]


def _flags(pattern):
    """All-caps acronyms (IT, AI, LAN...) match case-sensitively so ordinary words don't count."""
    letters = re.sub(r"\\[a-zA-Z]|[^a-zA-Z]", "", pattern)
    return 0 if letters and letters.isupper() else re.I


_compiled = [(name, [(re.compile(p.lstrip("~"), _flags(p.lstrip("~"))), p.startswith("~")) for p in pats])
             for name, pats in CATEGORIES]
# For ALL-CAPS text every acronym is upper case anyway, so match everything case-insensitively
_compiled_caps = [(name, [(re.compile(p.lstrip("~"), re.I), p.startswith("~")) for p in pats])
                  for name, pats in CATEGORIES]
_exclude = [re.compile(p, re.I) for p in EXCLUDE]


def classify(text):
    """Return (category, matched_terms) for IT tenders, or (None, []) if not IT."""
    letters = [c for c in text if c.isalpha()]
    caps = bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.6
    strong, weak = {}, {}
    for name, patterns in (_compiled_caps if caps else _compiled):
        for rx, is_weak in patterns:
            m = rx.search(text)
            if m:
                (weak if is_weak else strong).setdefault(name, []).append(m.group(0).lower())
    weak_terms = {t for v in weak.values() for t in v}
    excluded = any(rx.search(text) for rx in _exclude)
    if not strong and (len(weak_terms) < 2 or excluded):
        return None, []
    if strong and excluded and sum(len(v) for v in strong.values()) == 1 and not weak_terms:
        return None, []
    scores = {n: len(strong.get(n, [])) * 2 + len(weak.get(n, [])) for n in set(strong) | set(weak)}
    best = max(scores, key=scores.get)
    return best, sorted({t for d in (strong, weak) for v in d.values() for t in v})


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


# ---------------------------------------------------------------- briefing sessions
ONLINE_TERMS = re.compile(r"\b(virtual(ly)?|online|ms[ -]?teams|microsoft teams|teams (meeting|link)|zoom|webex|google meet|webinar|"
                          r"via (a )?link|link will be (sent|shared|provided|e-?mailed))\b", re.I)
PHYSICAL_TERMS = re.compile(r"\b(boardroom|board room|auditorium|committee room|conference room|venue:|building|"
                            r"\d{1,5}\s+\w+(\s\w+)?\s+(street|st|road|rd|avenue|ave|drive|dr)\b|on.?site|site (meeting|inspection|visit))", re.I)
MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
DATE_TEXT = re.compile(rf"\b(\d{{1,2}})(st|nd|rd|th)?\s+({MONTHS})\s+(\d{{4}})(?:\D{{1,25}}?(\d{{1,2}})\s*[h:.]\s*(\d{{2}}))?", re.I)
BRIEF_TEXT = re.compile(r"[^.\n]{0,160}\bbriefing\b[^.\n]{0,220}", re.I)
URL = re.compile(r"https?://\S+")


BRIEF_KEYS = {}  # key path -> example value, recorded so the output shows where eTenders puts briefing data


def find_briefing(obj, path=""):
    """Find briefing fields wherever eTenders puts them (tender.briefingSession, a release-level field, ...)."""
    found = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if "brief" in k.lower():
                if len(BRIEF_KEYS) < 20 and p not in BRIEF_KEYS:
                    BRIEF_KEYS[p] = v if not isinstance(v, (dict, list)) else json.dumps(v)[:300]
                if isinstance(v, dict):
                    found.update({kk: vv for kk, vv in v.items() if kk not in found})
                elif isinstance(v, list) and v and isinstance(v[0], dict):
                    found.update({kk: vv for kk, vv in v[0].items() if kk not in found})
                else:
                    found.setdefault(k, v)
            elif isinstance(v, (dict, list)) and k not in ("documents", "parties"):
                for kk, vv in find_briefing(v, p).items():
                    found.setdefault(kk, vv)
    elif isinstance(obj, list):
        for item in obj[:5]:
            for kk, vv in find_briefing(item, path).items():
                found.setdefault(kk, vv)
    return found


def pick_ci(d, *names):
    low = {k.lower(): v for k, v in d.items()}
    for n in names:
        v = low.get(n.lower())
        if v not in (None, ""):
            return v
    return None


def briefing_info(t, text, release=None):
    """Work out whether a tender has a briefing session, and whether it can be attended online.

    eTenders publishes a briefingSession object on the tender (isSession, compulsory, date, venue)
    when the department fills it in. Many departments only mention the briefing in the description,
    so fall back to reading that text.
    """
    bs = find_briefing(release if release is not None else {"tender": t})
    venue = str(pick_ci(bs, "venue", "briefingVenue", "location", "address", "briefingSessionVenue") or "").strip()
    held = pick_ci(bs, "isSession", "isBriefingSession", "briefingSession", "hasBriefing")
    if isinstance(held, str):
        held = held.strip().lower() in ("true", "yes", "1") if held.strip().lower() in ("true", "false", "yes", "no", "1", "0") else None
    elif not isinstance(held, bool):
        held = None
    compulsory = pick_ci(bs, "compulsory", "isCompulsory", "briefingCompulsory", "compulsoryBriefing", "mandatory")
    if isinstance(compulsory, str):
        compulsory = compulsory.strip().lower() in ("true", "yes", "1", "compulsory")
    elif not isinstance(compulsory, bool):
        compulsory = None
    raw_date = pick_ci(bs, "date", "briefingDate", "dateTime", "briefingDateTime", "startDate")
    date = parse_date(raw_date) if isinstance(raw_date, str) else None

    snippet = ""
    m = BRIEF_TEXT.search(text or "")
    if m:
        snippet = re.sub(r"\s+", " ", m.group(0)).strip()
        if held is None:
            held = not re.search(r"\bno (compulsory )?briefing\b|\bbriefing.{0,20}\bnot (be )?(held|applicable)\b", snippet, re.I)
        if compulsory is None:
            if re.search(r"\b(non|none|not)[ -]?compulsory\b|\boptional\b", snippet, re.I):
                compulsory = False
            elif re.search(r"\bcompulsory|mandatory\b", snippet, re.I):
                compulsory = True
        if not date:
            d = DATE_TEXT.search(snippet)
            if d:
                try:
                    hh, mm = int(d.group(5) or 0), int(d.group(6) or 0)
                    date = datetime.strptime(f"{d.group(1)} {d.group(3)} {d.group(4)}", "%d %B %Y").replace(
                        hour=hh if hh < 24 else 0, minute=mm if mm < 60 else 0, tzinfo=timezone(timedelta(hours=2)))
                except ValueError:
                    date = None

    where = f"{venue} {snippet}"
    online, physical = bool(ONLINE_TERMS.search(where)), bool(PHYSICAL_TERMS.search(where))
    if held is False:
        mode = "none"
    elif online and physical:
        mode = "online and in person"
    elif online:
        mode = "online"
    elif venue or held:
        mode = "in person"
    else:
        mode = "unknown"
    link = URL.search(where)
    return {
        "held": held,
        "compulsory": compulsory,
        "date": date.isoformat() if date else None,
        "venue": venue,
        "mode": mode,
        "online": mode in ("online", "online and in person"),
        "link": link.group(0).rstrip(".,);") if link else None,
        "note": snippet[:300] if not venue else "",
    }


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
    briefing = briefing_info(t, " ".join([description, t.get("eligibilityCriteria") or "", t.get("submissionMethodDetails") or ""]), release)
    province = t.get("province") or contact.get("region") or ""
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
        "province": province,
        "briefing": briefing,
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


def carry_over(path, tenders, covered_from, days):
    """When the API is slow and a run covers fewer days than asked, keep still-open tenders
    from the previous file that were published before this run's coverage started."""
    try:
        with open(path, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return 0
    if not covered_from:
        return 0
    now = datetime.now(timezone.utc)
    have = {t["id"] for t in tenders}
    added = 0
    for t in prev.get("tenders") or []:
        end = parse_date(t.get("closingDate"))
        published = (t.get("publishedDate") or "")[:10]
        if t.get("id") in have or not end or end < now or not published or published >= covered_from:
            continue
        t.setdefault("province", (t.get("contact") or {}).get("region", ""))
        if "briefing" not in t:
            t["briefing"] = briefing_info({}, " ".join([t.get("title", ""), t.get("eligibility", ""), t.get("submission", "")]), {})
        tenders.append(t)
        have.add(t["id"])
        added += 1
    if added:
        print(f"::notice::Kept {added} still-open tenders from the previous run (published before {covered_from})", file=sys.stderr)
    return added


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
    carried = carry_over(args.out, tenders, covered_from, args.days)
    if carried:
        tenders.sort(key=lambda x: x["closingDate"])
    cats = {}
    for t in tenders:
        cats[t["category"]] = cats.get(t["category"], 0) + 1
    online = sum(1 for t in tenders if (t.get("briefing") or {}).get("online"))

    payload = {
        "source": API_URL,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "lookbackDays": args.days,
        "coveredFrom": covered_from,
        "releasesScanned": scanned,
        "uniqueTenders": unique,
        "count": len(tenders),
        "categories": cats,
        "onlineBriefings": online,
        "carriedOver": carried,
        "briefingFieldsSeen": BRIEF_KEYS,
        "tenders": tenders,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)

    print(f"\nScanned {scanned} releases ({unique} unique tenders)")
    print(f"Open IT tenders: {len(tenders)} -> {args.out} ({online} with an online briefing)")
    for name, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {name}: {n}")


if __name__ == "__main__":
    main()
