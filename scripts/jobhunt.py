"""Bookkeeping for the job-hunt skill: workspace setup, triage, scoring, logging, gap report.

Standard library only. Usage:
  python jobhunt.py init   <workspace>
  python jobhunt.py triage <workspace> <run>   # dedupe, title and years filters
  python jobhunt.py score  <workspace> <run>   # JD skill coverage per job
  python jobhunt.py log    <workspace> <run>   # upsert results into state/applied.csv
  python jobhunt.py report <workspace> <run>   # reports/<run>-skill-gaps.md + state/scores.csv

<run> is a folder name under <workspace>/runs, normally today's date (YYYY-MM-DD).
The run's jobs live in runs/<run>/jobs.json, a list of job objects (see references/data.md).
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
APPLIED_COLUMNS = [
  "date", "company", "title", "cluster", "location", "url", "source",
  "status", "score", "resume_file", "note",
]
SCORE_COLUMNS = ["run", "cluster", "jobs", "avg_score"]
FINAL_STATUSES = {"applied", "needs_you", "failed", "skipped"}

# Spelling variants only. What the candidate actually knows lives in profile/skills.json.
ALIASES = {
  "k8s": "kubernetes", "llms": "llm", "large language models": "llm", "large language model": "llm",
  "genai": "generative ai", "gen ai": "generative ai", "gen-ai": "generative ai",
  "retrieval augmented generation": "rag", "retrieval-augmented generation": "rag",
  "postgres": "postgresql", "js": "javascript", "ts": "typescript", "golang": "go",
  "ci/cd": "ci cd", "cicd": "ci cd", "ci-cd": "ci cd", "ci/cd pipelines": "ci cd",
  "amazon web services": "aws", "gcp": "google cloud", "google cloud platform": "google cloud",
  "ml": "machine learning", "nlp": "natural language processing", "dsa": "data structures and algorithms",
  "node": "node.js", "nodejs": "node.js", "reactjs": "react", "react.js": "react",
  "rest apis": "rest api", "restful apis": "rest api", "rest": "rest api", "apis": "rest api",
  "huggingface": "hugging face", "hugging face transformers": "hugging face",
  "agents": "ai agents", "agentic ai": "ai agents", "llm agents": "ai agents", "ai agent": "ai agents",
  "agentic workflows": "ai agents", "multi-agent systems": "ai agents",
  "vector db": "vector database", "vector databases": "vector database", "vector dbs": "vector database",
  "vector store": "vector database", "prompting": "prompt engineering", "sklearn": "scikit-learn",
  "iac": "infrastructure as code", "terraform/iac": "terraform", "oop": "object oriented programming",
  "microsoft azure": "azure", "azure openai service": "azure openai", "aws bedrock": "amazon bedrock",
  "bedrock": "amazon bedrock", "evals": "llm evaluation", "llm evals": "llm evaluation",
  "model evaluation": "llm evaluation", "fine tuning": "fine-tuning", "finetuning": "fine-tuning",
}


def norm(skill: str) -> str:
  text = re.sub(r"\s+", " ", str(skill).strip().lower())
  text = re.sub(r"\s*\(.*?\)\s*", " ", text).strip(" .,;:")
  return ALIASES.get(text, text)


def load_json(path: Path, default):
  if not path.exists():
    return default
  return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict]:
  if not path.exists():
    return []
  with path.open(newline="", encoding="utf-8-sig") as handle:
    return list(csv.DictReader(handle))


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  with path.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


def job_key(job: dict) -> str:
  squash = lambda value: re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
  return f"{squash(job.get('company'))}|{squash(job.get('title'))}"


def url_key(url: str) -> str:
  return re.sub(r"[?#].*$", "", str(url or "").strip().lower()).rstrip("/")


def jobs_path(workspace: Path, run: str) -> Path:
  return workspace / "runs" / run / "jobs.json"


# ---------------------------------------------------------------- init
def cmd_init(workspace: Path) -> None:
  for folder in ("profile", "resumes", "runs", "reports", "state"):
    (workspace / folder).mkdir(parents=True, exist_ok=True)
  templates = SKILL_DIR / "assets" / "workspace"
  for template in templates.rglob("*"):
    if template.is_file():
      target = workspace / template.relative_to(templates)
      if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, target)
        print(f"created {target}")
  applied = workspace / "state" / "applied.csv"
  if not applied.exists():
    write_csv(applied, APPLIED_COLUMNS, [])
  print(f"workspace ready: {workspace}")


# -------------------------------------------------------------- triage
YEARS_PATTERN = re.compile(
  r"(\d{1,2})\s*(?:\+|plus)?\s*(?:-|–|to)?\s*(\d{1,2})?\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def min_years_from_text(text: str) -> int | None:
  """Lowest years figure the JD states as a requirement; None when it states none."""
  found = []
  for match in YEARS_PATTERN.finditer(text or ""):
    window = text[max(0, match.start() - 60): match.end() + 80].lower()
    if "experience" in window or "exp" in window:
      value = int(match.group(1))
      if value <= 20:
        found.append(value)
  # A JD often lists several figures ("5+ years overall, 2 years with LLMs"); the largest is the bar.
  return max(found) if found else None


def cmd_triage(workspace: Path, run: str) -> None:
  config = load_json(workspace / "config.json", {})
  max_years = config.get("max_required_years", 3)
  exclude = [word.lower() for word in config.get("exclude_title_words", [])]
  blocked_companies = [re.sub(r"[^a-z0-9]+", "", name.lower()) for name in config.get("exclude_companies", [])]
  jobs = load_json(jobs_path(workspace, run), [])
  applied = read_csv(workspace / "state" / "applied.csv")
  done_keys = {job_key(row) for row in applied if row.get("status") in {"applied", "skipped"}}
  done_urls = {url_key(row.get("url")) for row in applied if row.get("status") in {"applied", "skipped"}}
  # A tracker row with no title means "already applied at this company, role not recorded".
  squash = lambda value: re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
  done_companies = {squash(row.get("company")) for row in applied
                    if row.get("status") in {"applied", "skipped"} and not str(row.get("title") or "").strip()}
  done_urls.discard("")
  seen: set[str] = set()
  for job in jobs:
    if job.get("status") in FINAL_STATUSES:
      continue
    job["status"], job["drop_reason"] = "kept", ""
    key, title = job_key(job), str(job.get("title", "")).lower()
    company = squash(job.get("company"))
    if any(name and name in company for name in blocked_companies):
      job["status"], job["drop_reason"] = "dropped", "company on the user's never-apply list"
    elif company in done_companies:
      job["status"], job["drop_reason"] = "dropped", "already applied at this company"
    elif key in done_keys or url_key(job.get("url")) in done_urls:
      job["status"], job["drop_reason"] = "dropped", "already applied or skipped before"
    elif key in seen:
      job["status"], job["drop_reason"] = "dropped", "duplicate in this run"
    elif any(re.search(rf"\b{re.escape(word)}\b", title) for word in exclude):
      job["status"], job["drop_reason"] = "dropped", "title is above target level"
    else:
      if job.get("min_years") is None:
        job["min_years"] = min_years_from_text(job.get("description", ""))
      if job.get("min_years") is not None and job["min_years"] > max_years:
        job["status"] = "dropped"
        job["drop_reason"] = f"asks for {job['min_years']}+ years (limit {max_years})"
    seen.add(key)
  save_json(jobs_path(workspace, run), jobs)
  reasons = Counter(job["drop_reason"] for job in jobs if job["status"] == "dropped")
  print(f"{sum(job['status'] == 'kept' for job in jobs)} kept, {sum(reasons.values())} dropped of {len(jobs)}")
  for reason, count in reasons.most_common():
    print(f"  {count:>3}  {reason}")


# --------------------------------------------------------------- score
def known_skills(workspace: Path) -> set[str]:
  data = load_json(workspace / "profile" / "skills.json", {"skills": []})
  return {norm(skill) for skill in data.get("skills", [])}


def score_job(job: dict, known: set[str]) -> None:
  required = list(dict.fromkeys(norm(skill) for skill in job.get("required_skills", []) if str(skill).strip()))
  preferred = [skill for skill in dict.fromkeys(norm(s) for s in job.get("preferred_skills", []) if str(s).strip())
               if skill not in required]
  job["missing_required"] = [skill for skill in required if skill not in known]
  job["missing_preferred"] = [skill for skill in preferred if skill not in known]
  total = 2 * len(required) + len(preferred)
  matched = 2 * (len(required) - len(job["missing_required"])) + (len(preferred) - len(job["missing_preferred"]))
  job["score"] = round(100 * matched / total) if total else None


def cmd_score(workspace: Path, run: str) -> None:
  known = known_skills(workspace)
  jobs = load_json(jobs_path(workspace, run), [])
  for job in jobs:
    if job.get("status") != "dropped":
      score_job(job, known)
  save_json(jobs_path(workspace, run), jobs)
  scored = sorted((job for job in jobs if job.get("score") is not None), key=lambda job: -job["score"])
  for job in scored:
    missing = ", ".join(job["missing_required"][:4]) or "-"
    print(f"{job['score']:>3}  {job.get('cluster', '?'):<22} {job.get('company', '')} | {job.get('title', '')} | missing: {missing}")
  unscored = [job for job in jobs if job.get("status") != "dropped" and job.get("score") is None]
  if unscored:
    print(f"{len(unscored)} kept job(s) have no required_skills yet and were not scored")


# ----------------------------------------------------------------- log
def cmd_log(workspace: Path, run: str) -> None:
  path = workspace / "state" / "applied.csv"
  rows = read_csv(path)
  index = {(job_key(row), url_key(row.get("url"))): position for position, row in enumerate(rows)}
  written = 0
  for job in load_json(jobs_path(workspace, run), []):
    if job.get("status") not in FINAL_STATUSES:
      continue
    row = {
      "date": job.get("applied_on") or run, "company": job.get("company", ""), "title": job.get("title", ""),
      "cluster": job.get("cluster", ""), "location": job.get("location", ""), "url": job.get("url", ""),
      "source": job.get("source", ""), "status": job["status"],
      "score": "" if job.get("score") is None else job["score"],
      "resume_file": job.get("resume_file", ""), "note": job.get("note", ""),
    }
    key = (job_key(job), url_key(job.get("url")))
    if key in index:
      rows[index[key]] = row
    else:
      index[key] = len(rows)
      rows.append(row)
    written += 1
  write_csv(path, APPLIED_COLUMNS, rows)
  counts = Counter(row["status"] for row in rows)
  print(f"logged {written} job(s) from run {run}; tracker totals: {dict(counts)}")


# -------------------------------------------------------------- report
def cmd_report(workspace: Path, run: str) -> None:
  jobs = [job for job in load_json(jobs_path(workspace, run), []) if job.get("score") is not None]
  if not jobs:
    print("no scored jobs in this run; run `score` first")
    return
  notes = load_json(workspace / "runs" / run / "cluster_notes.json", {})
  clusters: dict[str, list[dict]] = defaultdict(list)
  for job in jobs:
    clusters[job.get("cluster") or "Other"].append(job)

  history = [row for row in read_csv(workspace / "state" / "scores.csv") if row.get("run") != run]
  previous: dict[str, dict] = {}
  for row in sorted(history, key=lambda row: row["run"]):
    previous[row["cluster"]] = row

  overall: Counter = Counter()
  spread: dict[str, set[str]] = defaultdict(set)
  lines = [f"# Skill gaps: run {run}", ""]
  lines += [f"{len(jobs)} job descriptions scored across {len(clusters)} clusters. The score is how much of a "
            "JD's listed skills your profile already covers (required skills count double). It is a keyword "
            "coverage measure, not any employer's real ATS score.", ""]
  lines += ["| Cluster | Jobs | Avg score | Last run | Change |", "|---|---|---|---|---|"]
  score_rows = []
  ordered = sorted(clusters.items(), key=lambda item: -len(item[1]))
  for cluster, members in ordered:
    average = round(sum(job["score"] for job in members) / len(members))
    score_rows.append({"run": run, "cluster": cluster, "jobs": len(members), "avg_score": average})
    before = previous.get(cluster)
    last = f"{before['avg_score']} ({before['run']})" if before else "-"
    change = f"{average - int(before['avg_score']):+d}" if before else "-"
    lines.append(f"| {cluster} | {len(members)} | {average} | {last} | {change} |")
  lines.append("")

  for cluster, members in ordered:
    gaps: Counter = Counter()
    for job in members:
      for skill in job.get("missing_required", []):
        gaps[skill] += 2
        overall[skill] += 2
        spread[skill].add(cluster)
      for skill in job.get("missing_preferred", []):
        gaps[skill] += 1
        overall[skill] += 1
        spread[skill].add(cluster)
    lines += [f"## {cluster}", ""]
    for point in notes.get(cluster, []):
      lines.append(f"- {point}")
    if notes.get(cluster):
      lines.append("")
    if gaps:
      lines.append("Missing most often: " + ", ".join(
        f"{skill} ({sum(skill in job.get('missing_required', []) + job.get('missing_preferred', []) for job in members)} of {len(members)})"
        for skill, _ in gaps.most_common(6)))
    else:
      lines.append("No gaps found in these JDs.")
    lines.append("")

  lines += ["## High-value skills to add", "",
            "Ranked by how often they were asked for and missing (required counts double).", "",
            "| Skill | Weight | Clusters |", "|---|---|---|"]
  for skill, weight in overall.most_common(10):
    lines.append(f"| {skill} | {weight} | {', '.join(sorted(spread[skill]))} |")
  lines += ["", "Add a skill to `profile/skills.json` only once you can honestly claim it; the score rises from there.", ""]

  report = workspace / "reports" / f"{run}-skill-gaps.md"
  report.parent.mkdir(parents=True, exist_ok=True)
  report.write_text("\n".join(lines), encoding="utf-8")
  write_csv(workspace / "state" / "scores.csv", SCORE_COLUMNS, history + score_rows)
  print(f"wrote {report}")


def main(argv: list[str]) -> int:
  if len(argv) < 3 or argv[1] not in {"init", "triage", "score", "log", "report"}:
    print(__doc__)
    return 2
  workspace = Path(argv[2]).expanduser()
  if argv[1] == "init":
    cmd_init(workspace)
    return 0
  run = argv[3] if len(argv) > 3 else date.today().isoformat()
  {"triage": cmd_triage, "score": cmd_score, "log": cmd_log, "report": cmd_report}[argv[1]](workspace, run)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
