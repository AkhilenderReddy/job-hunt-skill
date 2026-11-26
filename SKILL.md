---
name: job-hunt
description: Runs the user's personal job-hunt pipeline end to end - finds fresh job postings (Apify, Firecrawl, Google past-24-hours on company career pages), filters by years of experience and location eligibility, clusters them by the skills the job descriptions ask for, scores each against the user's profile, builds a tailored resume PDF per job, applies in the browser from the local JobHunt folder, tracks every application, and writes a skill-gap report with scores that can be compared run to run. Use this whenever the user wants to search for jobs, find new or recent openings, apply to a job or a list of jobs, tailor or customise a resume for a job description, check which skills their resume is missing, see their ATS or fit score, or review what they have already applied to - even if they only say "run the job hunt", "find me jobs", "apply to these" or paste a job link.
---

# Job hunt

One run takes the user from "find me jobs" to submitted applications plus a short report on what
their resume lacks. Work through the stages in order. Ask the user once at the start, then run
without interrupting until the end-of-run summary; anything that needs them is collected and raised
there, not one question at a time.

## Before the first run in a session

Uploads only work from folders the session can read. If the JobHunt folder is not one of the
session's folders, copy the run's PDFs to an allowed, git-ignored folder (currently
`C:\Users\Akhilender\Desktop\crackle\logs\job-hunt-resumes\<run>\`), or ask the user to add the JobHunt folder
to the session once.

## The workspace

Everything personal lives in one local folder, the workspace. Default:
`C:\Users\Akhilender\Documents\JobHunt`. If the user attached or named a different folder that holds
`config.json`, use that. If no workspace is reachable, ask for the folder before doing anything else.

```
JobHunt/
  config.json            defaults, roles, experience limit, location rules, title exclusions
  boards.json            company job boards read directly, per ATS (grows every run)
  site_notes.md          what has been learned about each application site
  profile/
    profile.json         contact details, work history, education, links
    answers.md           answers to application questions; the rules for what may be answered
    skills.json          skills the user can honestly claim (drives the score)
    master_resume.json   every true resume fact; tailored resumes are cut from this
    base_resume.pdf      the general resume, used when tailoring is skipped
  resumes/<run>/         tailored resume per job (.json, .html, .pdf)
  runs/<run>/jobs.json   this run's jobs and their state
  reports/               <run>-skill-gaps.md
  state/applied.csv      tracker of every application, all runs
  state/scores.csv       average score per cluster per run (the trend)
```

`<run>` is today's date, `YYYY-MM-DD`. Scripts are in this skill's `scripts/` folder; call them with
`python <skill>/scripts/jobhunt.py <command> <workspace> <run>`. A missing workspace is created with
`jobhunt.py init <workspace>`; then fill `profile/` with the user before the first run.

Read `config.json`, `profile/answers.md` and `profile/skills.json` at the start of every run.

## Models for each step

Use the cheapest model that does each step safely. Scripts cost nothing; model time is the cost.

| Step | Runs on | Why |
|---|---|---|
| Search, triage, score, report (`fetch_boards.py`, `linkedin_details.py`, `jobhunt.py`) | No model: plain scripts | Free and fast |
| Naukri profile refresh (once a day) and Naukri's own Apply | Subagent with `model: "haiku"` | Fixed routine; new questions stop and come back |
| Stage 3, reading postings | Subagents with `model: "haiku"`, about 20 postings each, in parallel | Simple extraction; the scripts re-check years afterwards |
| Stage 5, tailoring resumes | Sonnet subagent builds; the main session (Opus/Fable) reviews | Must stay truthful; once per cluster per run, from that day's postings |
| Stage 6, class A forms (LinkedIn Easy Apply, Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee, Breezy, JazzHR, Teamtailor, Personio, BambooHR) and Google Forms filling | Subagent with `model: "haiku"`, briefed with `references/apply-agent.md` | Standard single guest forms; anything new stops and comes back |
| Stage 6, class B forms (Phenom, Eightfold, Avature, Oracle, Zoho, PeopleStrong, custom sites) and Haiku's `stuck` jobs | Subagent with `model: "sonnet"` | Multi-step and quirky widgets need fewer mis-clicks |
| Stage 6, class D (Workday, Taleo, SuccessFactors, contactHR, account sites) | No model until the user signs in | Nothing an agent can do before that |
| Changing this skill, the run summary, anything unusual | The main session, Opus or Fable | Rare judgement calls |

The main session's model is the user's choice (the model picker); suggest Sonnet for long apply runs.
Subagents take `model` on the Agent call. When the main session runs on Opus or Fable, do not do the
"main session, Sonnet" steps there: hand them to a subagent with `model: "sonnet"` (briefed with
`references/apply-agent.md` plus `references/apply.md`), so each step runs on the model in this table.

**One browser agent at a time.** Tried 23 Nov 2026: three agents in parallel, each in its own tab,
all lost or swapped tabs, because the Chrome extension gives a session one shared tab group and
any agent can reset it. Run browser agents one after another. Parallelism goes into the non-browser
steps (reading postings, tailoring resumes), which can run while an applier works. If a future
setup gives each agent its own browser, raise this to 3. Keep each browser wave to about 10-12 jobs:
on 24 Nov 2026 the extension disconnected after ~15 company-site jobs in one Sonnet agent. Before a
wave that uses Google sign-in or Google Forms, check that Chrome's Google account is the one in
`answers.md`.

**Escalation.** Haiku goes first. Every job it reports `stuck` (a form it could not get through
that is not a sign-in or a missing answer) goes in the next wave to a Sonnet agent (`model:
"sonnet"`) with Haiku's note. Jobs that need the user (sign-in, account, captcha, a new question)
are told to the user as soon as each wave ends, grouped by site, while the other agents carry on.

## Naukri (every run)

Follow `references/naukri.md`: refresh the Naukri profile once per day (Haiku, first browser step),
search Naukri through Apify (no model), merge those jobs into the run, and apply in a Naukri Haiku
wave. A login page is a blocker for the user, never a password entry.

## Stage 1: Settings (usually no questions)

`config.json` holds `defaults` (roles, freshness, apply mode, how many). When they are set and the
user's message does not say otherwise, start straight away without asking: the user wants the whole
run to go from one line. Ask (one AskUserQuestion call) only for a setting that is missing, and save
the answer into `defaults` so it is not asked again.

- **Roles**: the roles in `config.json`.
- **How fresh**: past 24 hours unless told otherwise.
- **Apply mode**: `apply_all` (apply to everything that passes, then report) or `review_first`
  (show the shortlist and wait).
- **How many**: the target is volume, 100 or more postings scanned per day; apply to all that pass
  unless a cap is set.

If the user gave job links instead of asking for a search, skip Stage 2 and put those links into
`jobs.json` directly.

## Stage 2: Search

Read `references/search.md` first. Use the sources in this order and merge everything into
`runs/<run>/jobs.json` (fields in `references/data.md`):

1. **Free and direct** - `python <skill>/scripts/fetch_boards.py fetch <workspace> <run> --days 1`.
   Reads every company job board in `boards.json` through the ATS's public API (Greenhouse, Lever,
   Ashby, SmartRecruiters, Workable, Recruitee, Workday) plus LinkedIn's public search. No credits,
   no login. This is the main source.
2. **The user's Chrome** - job portals that only show good results when signed in (LinkedIn,
   Naukri, Wellfound, Instahyre). Open the portal's search with the past-24-hours filter and read
   the result pages as text.
3. **Apify and Firecrawl** - optional extras when credits are available; they add boards the first
   two miss.

Prefer the employer's own career page or ATS link over an aggregator link for the same job. Every
ATS job URL seen from any source is fed back with `fetch_boards.py add <workspace> <urls>` so that
company's board is read directly from then on.

Merge Apify and Firecrawl rows with `scripts/merge_extra.py <workspace> <run>` (file names in
`references/search.md`), then run `linkedin_details.py` to fill LinkedIn descriptions, then `jobhunt.py triage`. It removes duplicates, jobs already in the tracker, titles above the
user's level, and jobs whose text asks for more years than `config.json` allows.

## Stage 3: Read, filter, cluster

Open each kept job's posting (several at once; hand batches to subagents when there are more than
about 15). For each one fill in, from the posting itself:

- `min_years`: the experience the posting requires. Drop the job if it is above the limit.
- `location_ok`: apply the location rule in `config.json`. Drop the job when it fails, with the
  posting's own words as the reason. A posting that is closed, email-only, unpaid or a staffing
  repost hiding the employer is dropped too.
- `required_skills` and `preferred_skills`: short skill names as the posting states them (10 to 20
  in total is typical). Take them from the job description only; the user's resume plays no part in
  this step, because the gap report is only useful if it reflects what employers ask for.
- `cluster`: chosen from what the required skills are mostly about, not from the title. Clusters and
  how to tell them apart are in `references/data.md`.

Set `status` to `dropped` with a `drop_reason` for anything that fails, then run `jobhunt.py score`.
The score is the share of a posting's listed skills that `profile/skills.json` covers, with required
skills counting double. Say plainly when you report it that it measures keyword coverage and is not
any employer's real ATS score.

## Stage 4: Shortlist

Rank kept jobs (newest first, then score) and show a table: company, title, cluster, location, years
asked, score, top missing skills, and the plain URL (the user wants raw links). In `apply_all` mode
show the list and continue; in `review_first` mode ask which to apply to and apply only to those.
Jobs on a direct ATS page (Greenhouse, Lever, Ashby, Workable, SmartRecruiters) go first because
they can be finished without a login.

## Stage 5: Tailor the resume

For each selected job, follow `references/resume.md`: cut a one-page resume from
`profile/master_resume.json`, save it as `resumes/<run>/<Name>_<Role>_<Company>.json`, and build the
PDF with `scripts/build_resume.py`. Tailoring means choosing, ordering and wording true facts so the
posting's terms are visible. It never means adding a skill, tool, employer, date or number that is
not in the master resume: an invented claim can cost the user the job at interview or after hiring,
which is the opposite of what this skill is for. Skills the job wants and the user lacks go to the
gap report instead.

Jobs in the same cluster with near-identical skills can share one tailored resume.

**Build, then review (every run, never reuse yesterday's PDFs).** A Sonnet subagent builds one resume per
cluster from that cluster's postings in today's `jobs.json`: it counts the required skills, puts the
ones the user has first in Skills using the postings' own spelling, and works approaches the user
really has (distributed systems, client-facing delivery) into the Summary. The main session (Opus or
Fable) then reviews each JSON before the PDF is used: every frequently asked skill that is in
`skills.json` must be visible in Skills or the Summary; nothing may appear that is not in
`master_resume.json`; one page. It fixes what fails and rebuilds.

How the review runs, cheaply: (1) the Sonnet subagent writes all cluster JSONs in one go; (2) the
main session reviews them in a single pass against that cluster's postings, checking visible skills,
a clear Summary (approaches such as distributed systems included), the strongest bullets first,
nothing beyond the master, one page; (3) it edits the JSON itself, with no round trip back to
Sonnet, and rebuilds only the PDFs that changed; (4) any fix that would help every future resume
(a better master bullet, a clearer skills grouping, a rule) goes into `master_resume.json` or
`references/resume.md`, so the next run starts from the improved version. When a top gap skill keeps
appearing, ask the user once whether they have really used it; a yes goes into `skills.json` and
`master_resume.json`, a no stays in the gap report. The score only rises through true skills.

## Stage 6: Apply

Split the selected jobs first by form class (table in `references/apply.md`): A to Haiku, B to Sonnet, C filled by Haiku and finished by the user, D straight to the blocker list. On LinkedIn, the job page shows "Easy Apply" or "Apply on company
website" (whose link gives the employer URL). Hand the Easy Apply jobs, in batches of about ten, to
a Haiku subagent briefed with `references/apply-agent.md`. It applies only when every question is
answered in `answers.md`, and returns the rest with the exact new questions. Ask the user those
questions together, save the answers, and re-run the returned jobs. Do the company-website jobs in
the main session.

Follow `references/apply.md`. In short: open the apply link in the browser, upload the tailored PDF
from `resumes/<run>/`, answer from `profile/profile.json` and `profile/answers.md`, accept required
privacy or terms consents, decline optional cookies and marketing opt-ins, submit, and confirm the
submission really went through.

Consents never wait for the user: by applying, the user agrees to the employer using their data, so
tick every required acknowledgement, privacy, terms and data-processing box and submit.

Stop that one application and mark it `needs_you`, then carry on with the next job, when it needs a
login or new account, a captcha, a required question `answers.md` does not cover, or a legal or
ethics declaration that is not already confirmed there. Guessing these puts a false statement under
the user's name, so they wait for the user. Do every application that needs no login first, then
hand the user one list of blockers at the end; when they have signed in or answered, finish those.

After each job set `status` (`applied`, `needs_you`, `failed`, `skipped`), `resume_file`, `note`.

## Stage 7: Track and report

1. `jobhunt.py log` - updates `state/applied.csv`.
2. Write `runs/<run>/cluster_notes.json`: for each cluster, two or three short points on what its
   postings ask for (see `references/data.md`). Keep them factual and brief.
3. `jobhunt.py report` - writes `reports/<run>-skill-gaps.md` (per-cluster average score, change
   since the last run, most-missed skills, and the high-value skills to add) and updates
   `state/scores.csv`.

## End-of-run summary

Tell the user, briefly:

- how many were found, dropped (with the main reasons), applied, and waiting on them;
- each `needs_you` job with its link and exactly what is needed, and any new questions to add to
  `answers.md` (ask them now, save the answers there so the next run does not ask again);
- per-cluster score and how it moved since the last run;
- the top three to five skills to add, and the report path.

## Learning: every run leaves the skill better

The user should never be asked the same thing twice, and a problem solved once should stay solved.
Before ending a run, write down what it taught:

| Learned | Save it in |
|---|---|
| An answer the user gave to a form question (even a one-word "yes") | `profile/answers.md`, as question and answer, with the date |
| A skill the user now has | `profile/skills.json` (and `master_resume.json` when it belongs on the resume) |
| A company board or ATS link seen anywhere | `fetch_boards.py add` into `boards.json` |
| How a site's form behaves, what blocked it, what worked | `site_notes.md` in the workspace, one short entry per site |
| A preference about how runs should go (roles, mode, limits) | `config.json` `defaults` |
| A correction to the method itself, or a new idea the user asks for | this skill's own `SKILL.md` or `references/` files |

This skill folder is a git repo (private: github.com/AkhilenderReddy/job-hunt-skill). After
changing any skill file, commit it with a one-line message and push, so every machine and agent can
pull the improvement. Personal data never goes in this repo; it stays in the workspace.

Read `site_notes.md` before applying on a site it mentions. When the user suggests an improvement to
the process, change the skill files in the same turn and say what changed; do not just apply it to
the current run.
