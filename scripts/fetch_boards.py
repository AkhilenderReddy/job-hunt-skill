"""Free job sources for the job-hunt skill: company job boards (ATS public APIs) and LinkedIn's
public search pages. No Apify, no login, standard library only.

  python fetch_boards.py fetch <workspace> <run> [--days 1] [--no-linkedin]
  python fetch_boards.py add   <workspace> <url> [<url> ...]     # learn boards from any ATS job URLs
  python fetch_boards.py discover <workspace> [--limit 20000]    # bulk-learn boards from Common Crawl

`fetch` reads <workspace>/boards.json (company boards per ATS), pulls every board, keeps postings
that are recent, match the target roles and can be done from India, and merges them into
runs/<run>/jobs.json. Boards that no longer exist are remembered in boards.json under "dead" and
skipped next time. `add` grows boards.json from URLs seen anywhere (LinkedIn redirects, Google
results, links the user pastes), which is how coverage improves from run to run.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
ATS_KEYS = ["greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "workday"]
INDIA = ["india", "bengaluru", "bangalore", "hyderabad", "pune", "mumbai", "chennai", "gurgaon", "gurugram",
         "noida", "delhi", "kolkata", "ahmedabad", "kochi", "coimbatore", "jaipur", "indore", "chandigarh",
         "thiruvananthapuram", "trivandrum", "mohali", "vadodara", "nagpur", "bhubaneswar", "mysore", "mysuru"]
REMOTE = ["remote", "anywhere", "worldwide", "global", "apac", "asia"]
ELSEWHERE = ["united states", "usa", " us", "us-", "u.s.", "canada", "united kingdom", " uk", "europe", "emea",
             "latam", "americas", "north america", "germany", "france", "ireland", "australia", "israel",
             "singapore", "japan", "brazil", "mexico", "poland", "spain", "netherlands"]
DEFAULT_TITLE_KEYWORDS = [
  "ai ", " ai", "a.i", "ml ", " ml", "machine learning", "llm", "genai", "gen ai", "generative", "agentic",
  "applied", "forward deployed", "software engineer", "software developer", "sde", "backend", "back end",
  "full stack", "fullstack", "full-stack", "devops", "platform engineer", "site reliability", "sre",
  "mlops", "security engineer", "solutions engineer", "python", "member of technical staff", "developer",
]


def get(url: str, data: dict | None = None, timeout: int = 25):
  body = json.dumps(data).encode() if data is not None else None
  headers = {"User-Agent": UA, "Accept": "application/json, text/html;q=0.8"}
  if body:
    headers["Content-Type"] = "application/json"
  request = urllib.request.Request(url, data=body, headers=headers)
  with urllib.request.urlopen(request, timeout=timeout) as response:
    return response.read().decode("utf-8", "replace")


def text_of(markup: str | None, limit: int = 7000) -> str:
  raw = html.unescape(html.unescape(markup or ""))
  return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()[:limit]


def when(value) -> datetime | None:
  if value in (None, ""):
    return None
  try:
    if isinstance(value, (int, float)):
      return datetime.fromtimestamp(value / 1000 if value > 1e11 else value, tz=timezone.utc)
    parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
  except (ValueError, OSError):
    return None


def job(ats, board, title, location, url, posted, description="", remote=False) -> dict:
  return {"title": (title or "").strip(), "company": board, "location": (location or "").strip(), "url": url,
          "source": ats, "posted": posted.isoformat() if posted else "", "description": description,
          "remote": bool(remote), "_posted": posted}


# ------------------------------------------------------------------ ATS readers
def greenhouse(slug):
  data = json.loads(get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"))
  for item in data.get("jobs", []):
    yield job("greenhouse", item.get("company_name") or slug, item.get("title"),
              (item.get("location") or {}).get("name"), item.get("absolute_url"),
              when(item.get("first_published") or item.get("updated_at")), text_of(item.get("content")))


def lever(slug):
  for item in json.loads(get(f"https://api.lever.co/v0/postings/{slug}?mode=json")):
    cats = item.get("categories") or {}
    place = ", ".join(cats.get("allLocations") or [cats.get("location") or ""])
    lists = " ".join(f"{part.get('text', '')}: {text_of(part.get('content'))}" for part in item.get("lists") or [])
    yield job("lever", slug, item.get("text"), place, item.get("hostedUrl"), when(item.get("createdAt")),
              (text_of(item.get("descriptionPlain") or item.get("description")) + " " + lists)[:7000],
              (item.get("workplaceType") or "") == "remote")


def ashby(slug):
  data = json.loads(get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}"))
  for item in data.get("jobs", []):
    places = [item.get("location") or ""] + [s.get("location", "") for s in item.get("secondaryLocations") or []]
    yield job("ashby", slug, item.get("title"), ", ".join(p for p in places if p), item.get("jobUrl"),
              when(item.get("publishedAt")), text_of(item.get("descriptionPlain") or item.get("descriptionHtml")),
              item.get("isRemote"))


def smartrecruiters(slug):
  offset = 0
  while offset < 500:
    data = json.loads(get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}&country=in"))
    for item in data.get("content", []):
      place = item.get("location") or {}
      yield job("smartrecruiters", (item.get("company") or {}).get("name") or slug, item.get("name"),
                ", ".join(p for p in (place.get("city"), place.get("country")) if p),
                f"https://jobs.smartrecruiters.com/{slug}/{item.get('id')}", when(item.get("releasedDate")), "",
                place.get("remote"))
    offset += 100
    if offset >= data.get("totalFound", 0):
      break


def workable(slug):
  data = json.loads(get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true"))
  for item in data.get("jobs", []):
    yield job("workable", data.get("name") or slug, item.get("title"),
              ", ".join(p for p in (item.get("city"), item.get("country")) if p),
              item.get("url") or item.get("shortlink"), when(item.get("published_on") or item.get("created_at")),
              text_of(item.get("description")), item.get("telecommuting"))


def recruitee(slug):
  data = json.loads(get(f"https://{slug}.recruitee.com/api/offers/"))
  for item in data.get("offers", []):
    yield job("recruitee", item.get("company_name") or slug, item.get("title"),
              ", ".join(p for p in (item.get("city"), item.get("country")) if p), item.get("careers_url"),
              when((item.get("published_at") or "").replace(" UTC", "+00:00").replace(" ", "T", 1)),
              text_of(item.get("description")) + " " + text_of(item.get("requirements")), item.get("remote"))


def workday(spec):
  tenant, host, site = spec.split("|")
  base = f"https://{tenant}.{host}.myworkdayjobs.com"
  for offset in range(0, 60, 20):
    data = json.loads(get(f"{base}/wday/cxs/{tenant}/{site}/jobs",
                          {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": "India engineer"}))
    rows = data.get("jobPostings", [])
    for item in rows:
      label = (item.get("postedOn") or "").lower()
      days = 0 if "today" in label else 1 if "yesterday" in label else int((re.search(r"(\d+)", label) or [0, 99])[1])
      yield job("workday", tenant, item.get("title"), item.get("locationsText"),
                f"{base}/en-US/{site}{item.get('externalPath', '')}",
                datetime.now(timezone.utc) - timedelta(days=days), "")
    if len(rows) < 20:
      break


READERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "smartrecruiters": smartrecruiters,
           "workable": workable, "recruitee": recruitee, "workday": workday}


# ------------------------------------------------------------------ LinkedIn public search
def linkedin(keywords: str, days: int, pages: int = 4):
  seconds = 86400 * days
  for page in range(pages):
    query = urllib.parse.urlencode({"keywords": keywords, "location": "India", "f_TPR": f"r{seconds}",
                                    "sortBy": "DD", "start": page * 25})
    try:
      markup = get(f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{query}")
    except (urllib.error.URLError, TimeoutError):
      return
    cards = re.split(r"<li>", markup)[1:]
    if not cards:
      return
    for card in cards:
      link = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"?]+)', card)
      title = re.search(r'base-search-card__title[^>]*>\s*([^<]+)', card)
      company = re.search(r'base-search-card__subtitle[^>]*>\s*(?:<a[^>]*>)?\s*([^<]+)', card)
      place = re.search(r'job-search-card__location[^>]*>\s*([^<]+)', card)
      posted = re.search(r'datetime="([^"]+)"', card)
      if link and title:
        row = job("linkedin", html.unescape((company.group(1) if company else "").strip()),
                  html.unescape(title.group(1)), html.unescape(place.group(1) if place else "India"),
                  link.group(1), when(posted.group(1)) if posted else None)
        row["recent_by_source"] = True  # LinkedIn already applied the time filter; cards carry dates only
        yield row
    time.sleep(1.2)


# ------------------------------------------------------------------ filters
def place_ok(row: dict) -> bool:
  place = f" {row['location'].lower()} "
  if any(city in place for city in INDIA):
    return True
  if row["remote"] or any(word in place for word in REMOTE):
    return not any(region in place for region in ELSEWHERE)
  return False


def title_ok(title: str, keywords: list[str], exclude: list[str]) -> bool:
  low = f" {title.lower()} "
  if any(re.search(rf"\b{re.escape(word)}\b", low) for word in exclude):
    return False
  return any(word in low for word in keywords)


def url_key(url: str) -> str:
  return re.sub(r"[?#].*$", "", str(url or "").strip().lower()).rstrip("/")


def cmd_fetch(workspace: Path, run: str, days: int, use_linkedin: bool) -> None:
  config = json.loads((workspace / "config.json").read_text(encoding="utf-8"))
  boards_path = workspace / "boards.json"
  boards = json.loads(boards_path.read_text(encoding="utf-8")) if boards_path.exists() else {}
  dead = set(boards.get("dead", []))
  keywords = config.get("title_keywords") or DEFAULT_TITLE_KEYWORDS
  exclude = [word.lower() for word in config.get("exclude_title_words", [])]
  cutoff = datetime.now(timezone.utc) - timedelta(days=days, hours=6)
  tasks = [(ats, slug) for ats in ATS_KEYS for slug in boards.get(ats, []) if f"{ats}:{slug}" not in dead]
  parallel_tasks = [task for task in tasks if task[0] != "workday"]

  def pull(task):
    ats, slug = task
    try:
      return task, list(READERS[ats](slug)), None
    except urllib.error.HTTPError as error:
      return task, [], error.code
    except Exception as error:  # network trouble on one board must not stop the run
      return task, [], str(error)[:60]

  found, stats, problems = [], {}, []
  with ThreadPoolExecutor(max_workers=12) as pool:
    for (ats, slug), rows, error in pool.map(pull, parallel_tasks):
      entry = stats.setdefault(ats, {"boards": 0, "open": 0, "matched": 0})
      if error in (404, 410):
        dead.add(f"{ats}:{slug}")
        continue
      if error:
        problems.append(f"{ats}:{slug} ({error})")
        continue
      entry["boards"] += 1
      entry["open"] += len(rows)
      for row in rows:
        if row["_posted"] and row["_posted"] >= cutoff and title_ok(row["title"], keywords, exclude) and place_ok(row):
          found.append(row)
          entry["matched"] += 1
  # Workday rate-limits parallel bursts (HTTP 429), so its boards are read one at a time.
  workday_boards = [slug for ats, slug in tasks if ats == "workday"]
  if workday_boards:
    entry = stats["workday"] = {"boards": 0, "open": 0, "matched": 0}
    problems = [p for p in problems if not p.startswith("workday:")]
    for slug in workday_boards:
      for attempt in range(3):
        try:
          rows = list(workday(slug))
          break
        except urllib.error.HTTPError as error:
          rows = None
          if error.code in (404, 410, 422):
            break
          time.sleep(4 * (attempt + 1))
        except Exception:
          rows = None
          break
      if rows is None:
        problems.append(f"workday:{slug}")
        continue
      entry["boards"] += 1
      entry["open"] += len(rows)
      for row in rows:
        if row["_posted"] >= cutoff and title_ok(row["title"], keywords, exclude) and place_ok(row):
          found.append(row)
          entry["matched"] += 1
      time.sleep(1.5)
  if use_linkedin:
    # One search per role term: LinkedIn returns at most ~100 cards per search, so many narrow
    # searches find far more than a few broad OR-queries.
    entry = stats.setdefault("linkedin", {"boards": 0, "open": 0, "matched": 0})
    terms = [term for group in (config.get("roles") or {}).values() for term in group]
    for term in dict.fromkeys(terms):
      for row in linkedin(f'"{term}"', days):
        entry["open"] += 1
        if title_ok(row["title"], keywords, exclude):
          found.append(row)
          entry["matched"] += 1
      entry["boards"] += 1

  path = workspace / "runs" / run / "jobs.json"
  jobs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
  seen = {url_key(item.get("url")) for item in jobs}
  added = 0
  for row in found:
    row.pop("_posted", None)
    if url_key(row["url"]) not in seen:
      seen.add(url_key(row["url"]))
      jobs.append(row)
      added += 1
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
  boards["dead"] = sorted(dead)
  boards_path.write_text(json.dumps(boards, indent=2) + "\n", encoding="utf-8")
  print(f"{'source':<16}{'boards':>7}{'open jobs':>11}{'matched':>9}")
  for ats, entry in stats.items():
    print(f"{ats:<16}{entry['boards']:>7}{entry['open']:>11}{entry['matched']:>9}")
  print(f"added {added} new job(s) to {path} (now {len(jobs)}); {len(dead)} dead board(s) remembered")
  if problems:
    print(f"{len(problems)} board(s) had errors: " + ", ".join(problems[:12]))


PATTERNS = [
  ("greenhouse", r"(?:job-boards|boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)"),
  ("lever", r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]+)"),
  ("ashby", r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)"),
  ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)"),
  ("workable", r"apply\.workable\.com/([A-Za-z0-9_-]+)"),
  ("recruitee", r"https?://([a-z0-9-]+)\.recruitee\.com"),
]
WORKDAY = r"https?://([a-z0-9_-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)"


def cmd_add(workspace: Path, urls: list[str]) -> None:
  path = workspace / "boards.json"
  boards = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
  added = []
  for url in urls:
    match = re.search(WORKDAY, url)
    hit = ("workday", "|".join(match.groups())) if match else None
    for ats, pattern in PATTERNS:
      found = re.search(pattern, url)
      if found and not hit:
        hit = (ats, urllib.parse.unquote(found.group(1)))
    if hit and hit[1].lower() not in {"embed", "j", "jobs", "api"}:
      known = boards.setdefault(hit[0], [])
      if hit[1] not in known:
        known.append(hit[1])
        added.append(f"{hit[0]}:{hit[1]}")
  path.write_text(json.dumps(boards, indent=2) + "\n", encoding="utf-8")
  print(f"added {len(added)} board(s): {', '.join(added[:40]) or '-'}{' ...' if len(added) > 40 else ''}")


CRAWL_PATTERNS = ["job-boards.greenhouse.io/*", "boards.greenhouse.io/*", "jobs.lever.co/*", "jobs.ashbyhq.com/*",
                  "apply.workable.com/*"]


def cmd_discover(workspace: Path, limit: int) -> None:
  """Bulk-learn boards from the Common Crawl index (a free public index of crawled URLs)."""
  collections = json.loads(get("https://index.commoncrawl.org/collinfo.json", timeout=60))
  api = collections[0]["cdx-api"]
  print(f"using {collections[0]['id']}")
  urls: list[str] = []
  for pattern in CRAWL_PATTERNS:
    query = urllib.parse.urlencode({"url": pattern, "output": "json", "fl": "url", "limit": limit})
    for attempt in range(3):
      try:
        lines = get(f"{api}?{query}", timeout=180).splitlines()
        urls += [json.loads(line)["url"] for line in lines if line.startswith("{")]
        print(f"  {pattern}: {len(lines)} urls")
        break
      except Exception as error:
        print(f"  {pattern}: attempt {attempt + 1} failed ({str(error)[:50]})")
        time.sleep(5 * (attempt + 1))
  cmd_add(workspace, urls)


def main(argv: list[str]) -> int:
  if len(argv) < 3 or argv[1] not in {"fetch", "add", "discover"}:
    print(__doc__)
    return 2
  workspace = Path(argv[2]).expanduser()
  if argv[1] == "add":
    cmd_add(workspace, argv[3:])
    return 0
  if argv[1] == "discover":
    cmd_discover(workspace, int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 20000)
    return 0
  days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 1
  cmd_fetch(workspace, argv[3], days, "--no-linkedin" not in argv)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
