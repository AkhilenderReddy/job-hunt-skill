"""Merge extra search results into runs/<run>/jobs.json.

  python merge_extra.py <workspace> <run>

Reads, when present, runs/<run>/apify_linkedin.json (raw items from valig/linkedin-jobs-scraper,
downloaded from https://api.apify.com/v2/datasets/<id>/items?clean=true&format=json&omit=descriptionHtml)
and runs/<run>/firecrawl_extra.json (a list of {company,title,location,url,source,posted}).
Rows already in jobs.json (same URL or LinkedIn job id) are skipped. Run it after fetch_boards.py fetch
and before jobhunt.py triage.
"""
import json, re, sys
from pathlib import Path


def key(url):
  m = re.search(r"linkedin\.com/jobs/view/(?:[^/]*-)?(\d+)", url or "")
  return "li:" + m.group(1) if m else (url or "").split("?")[0].rstrip("/").lower()


def main(workspace, run):
  folder = Path(workspace) / "runs" / run
  path = folder / "jobs.json"
  jobs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
  seen = {key(j.get("url")) for j in jobs}
  rows = []
  apify = folder / "apify_linkedin.json"
  if apify.exists():
    for r in json.loads(apify.read_text(encoding="utf-8")):
      rows.append({"title": r.get("title"), "company": r.get("companyName"), "location": r.get("location"),
                   "url": r.get("url") or "", "apply_url": r.get("applyUrl") or "", "apply_type": r.get("applyType") or "",
                   "source": "apify-linkedin", "posted": (r.get("postedDate") or "")[:10],
                   "seniority": r.get("experienceLevel"), "employment": r.get("contractType"),
                   "applicants": r.get("applicationsCount"), "description": (r.get("description") or "")[:7000]})
  naukri = folder / "apify_naukri.json"
  if naukri.exists():
    for r in json.loads(naukri.read_text(encoding="utf-8")):
      url = r.get("jdURL") or r.get("url") or r.get("jobUrl") or ""
      if url and url.startswith("/"):
        url = "https://www.naukri.com" + url
      rows.append({"title": r.get("title") or r.get("jobTitle"), "company": r.get("companyName") or r.get("company"),
                   "location": r.get("location") or ", ".join(r.get("locations") or []) if isinstance(r.get("locations"), list) else (r.get("location") or ""),
                   "url": url, "source": "apify-naukri", "posted": str(r.get("createdDate") or r.get("postedDate") or "")[:10],
                   "experience": r.get("experience") or r.get("experienceText"), "description": str(r.get("jobDescription") or r.get("description") or "")[:7000]})
  extra = folder / "firecrawl_extra.json"
  if extra.exists():
    rows += json.loads(extra.read_text(encoding="utf-8"))
  added = 0
  for row in rows:
    if key(row.get("url")) in seen:
      continue
    seen.add(key(row.get("url")))
    row["status"] = "new"
    jobs.append(row)
    added += 1
  path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"merged {added} extra job(s); now {len(jobs)}")


if __name__ == "__main__":
  main(*sys.argv[1:3])
