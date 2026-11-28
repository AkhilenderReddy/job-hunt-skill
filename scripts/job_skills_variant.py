"""Make a per-job resume variant that lists the job's missing required skills in the Skills section.

  python job_skills_variant.py <workspace> <run> <idx> [<idx> ...]

For each job index in runs/<run>/jobs.json: takes the job's cluster resume JSON
(resume_file with .json), adds every skill in the job's `missing_required` to the best-matching Skills
subsection (languages, backend/frameworks, cloud/devops, AI/ML, otherwise the last group), and builds
resumes/<run>/variants/<Name>_<idx>.pdf with build_resume.py. Experience, projects and every other
section are left exactly as they are: added skills appear ONLY in the Skills section (user's rule,
28 Nov 2026). Updates the job's resume_file to the variant and prints one line per job.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent

GROUP_HINTS = [
  (r"\b(go|golang|java|kotlin|scala|c#|c\+\+|ruby|rust|php|swift|typescript|javascript|python|dart)\b", ["program", "language"]),
  (r"spring|django|\.net|rails|laravel|express|nest|flask|fastapi|node|react|angular|vue|next|graphql|grpc|kafka|redis|mysql|postgres|mongo|sql|api",
   ["backend", "web", "data", "database"]),
  (r"aws|azure|gcp|google cloud|kubernetes|docker|terraform|ansible|jenkins|helm|ci/cd|devops|linux|prometheus|grafana",
   ["cloud", "devops", "platform", "infra"]),
  (r"llm|rag|agent|ml|ai|nlp|pytorch|tensorflow|embedding|vector|langchain|langgraph|genai|generative",
   ["ai", "llm", "ml"]),
]


def pick_group(skill: str, groups: list[dict]) -> dict:
  s = skill.lower()
  for pattern, hints in GROUP_HINTS:
    if re.search(pattern, s):
      for g in groups:
        if any(h in g["group"].lower() for h in hints):
          return g
  return groups[-1]


def main(workspace: str, run: str, idxs: list[str]) -> None:
  ws = Path(workspace)
  jobs_path = ws / "runs" / run / "jobs.json"
  jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
  out_dir = ws / "resumes" / run / "variants"
  out_dir.mkdir(parents=True, exist_ok=True)
  for raw in idxs:
    i = int(raw)
    job = jobs[i]
    base_pdf = ws / job["resume_file"]
    base_json = base_pdf.with_suffix(".json")
    resume = json.loads(base_json.read_text(encoding="utf-8"))
    present = " ".join(g["items"].lower() for g in resume["skills"])
    added = []
    for skill in job.get("missing_required") or []:
      if skill.lower() in present:
        continue
      group = pick_group(skill, resume["skills"])
      group["items"] += ", " + skill
      present += " " + skill.lower()
      added.append(skill)
    name = f"{base_pdf.stem}_{i}"
    vjson = out_dir / f"{name}.json"
    vpdf = out_dir / f"{name}.pdf"
    vjson.write_text(json.dumps(resume, indent=2, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run([sys.executable, str(SKILL_DIR / "build_resume.py"), str(vjson), str(vpdf)],
                            capture_output=True, text=True)
    job["resume_file"] = str(vpdf.relative_to(ws)).replace("\\", "/")
    job["skills_added_to_resume"] = added
    print(f"{i} | {job.get('company')} | added: {', '.join(added) or 'none'} | {result.stdout.strip().splitlines()[-1] if result.stdout.strip() else result.stderr.strip()[-200:]}")
  jobs_path.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
  main(sys.argv[1], sys.argv[2], sys.argv[3:])
