# YC / Work at a Startup flow (daily, low volume, high value)

Every Apply on ycombinator.com/jobs goes to Work at a Startup (WaaS): one YC account and one profile,
then one click plus an optional short note to the founder per job. Most YC roles are US-only or
"Remote (US)", so few fit an India-based candidate on a given day; checking is cheap, so check daily.

| # | Step | How | Model |
|---|---|---|---|
| 1 | Search | Firecrawl Alexandria `ycombinator-com` `companies/job_search`, two calls in one `alexandria_library_read`: `{"country": "IN", "role": "eng", "page_size": 50}` and `{"role": "eng", "remote_only": true, "page_size": 50}`. Save the records to `runs/<run>/yc_jobs.json`. About 10 credits. | No model |
| 2 | Filter | Keep: `countries` contains IN, or `remote` is remote with empty `remote_countries` (or containing IN) and `visa` not "US citizen/visa only"; `minExperience` at or under `config.json` `max_required_years`; title not above level; employer not on the never-apply list; not already in the tracker. `merge_extra.py` merges `yc_jobs.json`. | No model |
| 3 | Read | Fetch each kept job's `url` and extract skills, cluster, years (Stage 3). Usually 0-5 a day. | Haiku |
| 4 | Founder note | For each job, a 2-3 sentence note: who the user is in the role's terms, the one master-resume project closest to the company's product (company one-liner from the YC profile), and availability. Facts only from `master_resume.json`; no flattery, no new claims. Save notes in `runs/<run>/yc_notes.json`. | Sonnet, all notes in one batch, no browser |
| 5 | Apply | In the signed-in Chrome: open `https://www.workatastartup.com/jobs/<id>` (id = record `id`), click Apply, paste the job's note, submit, confirm "Applied". A YC sign-in page = `needs_signin` (the user signs in; never type a password). | Haiku |
| 6 | Profile upkeep, weekly | On WaaS "My profile": job-search status "actively looking", resume = latest main PDF, India/remote preferences intact. Change nothing else without the user's say-so. Record `last_profile_check` in `state/yc.json`. | Haiku |
| 7 | Track | Tracker rows with `source: yc`. | No model |

The first time, show the user two sample founder notes and save their approval (or edits) as the
note style in `answers.md`; after that, notes go out without asking unless a company is unusual.
