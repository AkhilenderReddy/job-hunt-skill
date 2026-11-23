"""Enrich LinkedIn rows in a run with the full description and the employer's own apply link.

  python linkedin_details.py <workspace> <run>

Reads LinkedIn's public job page for every row whose source is "linkedin" and that has no
description yet. Fills `description`, `seniority`, `employment_type`, `applicants` and, when the job
applies off LinkedIn, `employer_url` (the company or ATS page; the row's `url` is switched to it).
Every ATS link found is added to boards.json via fetch_boards.add, so that company's board is read
directly next time. Standard library only; about one page per second to stay polite.
"""
from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch_boards import UA, cmd_add, text_of  # noqa: E402


def page(job_id: str) -> str:
  request = urllib.request.Request(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}",
                                   headers={"User-Agent": UA, "Accept": "text/html"})
  with urllib.request.urlopen(request, timeout=25) as response:
    return response.read().decode("utf-8", "replace")


def employer_link(markup: str) -> str:
  code = re.search(r'<code id="applyUrl"[^>]*>\s*<!--\s*"?(.*?)"?\s*-->', markup, re.S)
  if not code:
    return ""
  raw = html.unescape(code.group(1)).strip().strip('"')
  inner = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query).get("url", [raw])[0]
  return inner if inner.startswith("http") and "linkedin.com" not in inner else ""


def criteria(markup: str) -> dict:
  pairs = re.findall(r'description__job-criteria-subheader[^>]*>\s*([^<]+?)\s*<.*?'
                     r'description__job-criteria-text[^>]*>\s*([^<]+?)\s*<', markup, re.S)
  return {key.strip().lower(): value.strip() for key, value in pairs}


def main(argv: list[str]) -> int:
  if len(argv) != 3:
    print(__doc__)
    return 2
  workspace, run = Path(argv[1]), argv[2]
  path = workspace / "runs" / run / "jobs.json"
  jobs = json.loads(path.read_text(encoding="utf-8"))
  ats_links, done, failed = [], 0, 0
  for row in jobs:
    if row.get("source") != "linkedin" or row.get("description"):
      continue
    match = re.search(r"(\d{8,})", row.get("listing_url") or row.get("url") or "")
    if not match:
      continue
    try:
      markup = page(match.group(1))
    except Exception:
      failed += 1
      continue
    body = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', markup, re.S)
    row["description"] = text_of(body.group(1)) if body else ""
    facts = criteria(markup)
    row["seniority"] = facts.get("seniority level", "")
    row["employment_type"] = facts.get("employment type", "")
    applicants = re.search(r'num-applicants__caption[^>]*>\s*([^<]+?)\s*<', markup)
    row["applicants"] = applicants.group(1).strip() if applicants else ""
    link = employer_link(markup)
    row.setdefault("listing_url", row.get("url"))
    if link:
      row["employer_url"] = link
      row["url"] = link
      ats_links.append(link)
    done += 1
    time.sleep(1.0)
  path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"enriched {done} LinkedIn job(s), {failed} failed; {len(ats_links)} have an employer apply link")
  if ats_links:
    cmd_add(workspace, ats_links)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
