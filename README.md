# job-hunt skill

A personal agent skill that runs a job hunt end to end. It searches fresh postings, filters them by
experience and location, clusters them by the skills the job descriptions ask for, builds a
tailored one-page resume per cluster, applies in the browser, tracks every application, and writes
a skill-gap report whose scores can be compared run to run.

The skill holds no personal data. Everything personal (profile, application answers, resumes,
tracker) lives in a separate local workspace folder, by default `Documents/JobHunt`.

## Install

Claude Code (any machine):

```bash
git clone https://github.com/<your-user>/job-hunt-skill.git ~/.claude/skills/job-hunt
```

To update later: `git -C ~/.claude/skills/job-hunt pull`.

Other agents: point them at `SKILL.md`; it links to everything else under `references/` and
`scripts/`.

## First run

1. `python scripts/jobhunt.py init <workspace>` creates the workspace with `config.json` and `boards.json`.
2. Fill `profile/` (`profile.json`, `answers.md`, `skills.json`, `master_resume.json`, `base_resume.pdf`).
3. Say "run the job hunt".

## Layout

| Path | What it is |
|---|---|
| `SKILL.md` | The workflow the agent follows |
| `references/` | Search sources, data formats, resume rules, applying, the Easy Apply agent brief |
| `scripts/` | `fetch_boards.py` (free ATS + LinkedIn search), `linkedin_details.py`, `jobhunt.py` (triage, score, log, report), `build_resume.py` (JSON to PDF) |
| `assets/workspace/` | Templates copied into a new workspace |

Scripts need Python 3.10+ only (standard library); resume PDFs need Chrome or Edge.
