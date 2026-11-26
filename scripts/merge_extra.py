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


def epoch_day(value):
  try:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
  except (TypeError, ValueError):
    return str(value or "")[:10]


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
      comp = r.get("company") or {}
      exp = r.get("experience") or {}
      desc = r.get("description") or {}
      locs = r.get("locations") or []
      rows.append({"title": r.get("title"), "company": comp.get("name") if isinstance(comp, dict) else comp,
                   "location": ", ".join(l.get("label", str(l)) if isinstance(l, dict) else str(l) for l in locs) if isinstance(locs, list) else str(locs),
                   "url": r.get("url") or "", "source": "apify-naukri", "posted": epoch_day(r.get("createdDate")),
                   "naukri_company_apply": str(r.get("companyApplyJob")).lower() == "true",
                   "min_years_listed": exp.get("minimum") if isinstance(exp, dict) else None,
                   "description": str(desc.get("full") if isinstance(desc, dict) else desc or "")[:7000]})
  yc = folder / "yc_jobs.json"
  if yc.exists():
    for r in json.loads(yc.read_text(encoding="utf-8")):
      rows.append({"title": r.get("title"), "company": r.get("company_name"), "location": r.get("location") or "",
                   "url": r.get("url") or "", "apply_url": f"https://www.workatastartup.com/jobs/{r.get('id')}",
                   "source": "yc", "posted": r.get("createdAt") or "", "yc_batch": r.get("company_batch"),
                   "yc_min_experience": r.get("minExperience"), "visa": r.get("visa"), "salary": r.get("salaryRange"),
                   "remote": r.get("remote"), "remote_countries": r.get("remote_countries"), "description": ""})
  def first(r, *keys):
    for k in keys:
      v = r
      for part in k.split("."):
        v = v.get(part) if isinstance(v, dict) else None
      if v:
        return v
    return ""
  for name, src in (("apify_wellfound.json", "wellfound"), ("apify_instahyre.json", "instahyre")):
    f = folder / name
    if not f.exists():
      continue
    for r in json.loads(f.read_text(encoding="utf-8")):
      loc = first(r, "location", "locations", "jobLocation", "city")
      rows.append({"title": first(r, "title", "jobTitle", "role"), "company": first(r, "companyName", "company.name", "company", "employer"),
                   "location": ", ".join(map(str, loc)) if isinstance(loc, list) else str(loc),
                   "url": first(r, "publicUrl", "url", "jobUrl", "applyUrl", "link"), "source": src,
                   "posted": str(first(r, "postedDate", "datePosted", "postedAt", "createdAt"))[:10],
                   "remote": first(r, "remote", "isRemote", "remoteType"),
                   "experience": first(r, "yearsExperienceMin", "experienceMin", "experience", "experienceRange", "minExperience"),
                   "accepted_remote": first(r, "acceptedRemoteLocations"),
                   "description": str(first(r, "description", "jobDescription", "descriptionText"))[:7000]})
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
