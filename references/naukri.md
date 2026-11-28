# Naukri flow (daily)

Naukri ranks recently updated profiles higher, so the profile is refreshed once a day, then the day's
recent Naukri jobs go through the normal pipeline. The browser is used only for the refresh and for
applying; searching costs no model time.

| # | Step | How | Model |
|---|---|---|---|
| 1 | Profile refresh, once per day, first browser step of the run | See "Refresh" below. Skip if `state/naukri.json` `last_refresh` is today. | Haiku subagent |
| 2 | Search | Apify `valig/naukri-jobs-scraper`, one call: `{"keywords": "<roles joined with commas>", "jobAge": "1", "experience": <each of config naukri_experience_values: 0, 1, 2 - one call each, merged>, "sort": "f", "jobPostType": ["1"], "limit": 150}`. Save items as `runs/<run>/apify_naukri.json`; `merge_extra.py` merges them. | No model |
| 3 | Triage, read, score | The normal Stage 2-3 pipeline (never-apply list and category rule apply; duplicates of the same job found on LinkedIn or company boards are dropped) | Scripts + Haiku readers |
| 4 | Resume | The run's cluster resumes | none extra |
| 5 | Apply | Naukri's own "Apply" (class A) -> Haiku wave of about 10. "Apply on company site" -> route by form class (`references/apply.md`). | Haiku; class B Sonnet |
| 6 | Track | `source: naukri` rows in the tracker; new answers to `answers.md`; quirks to `site_notes.md` | No model |

## Refresh (Haiku brief)

1. Open `https://www.naukri.com/mnjuser/profile` in the user's signed-in Chrome. A login page means
   `needs_signin`: stop and report; never type a password or request an OTP.
2. Resume section: "Update resume" -> `file_upload` the run's main resume PDF (AI Engineer cluster
   unless the user says otherwise). Wait for the upload confirmation.
3. Resume headline: open the edit pencil, change nothing, Save (this alone also bumps the date).
4. Confirm the profile shows "Last updated: Today" (or today's date), then write
   `{"last_refresh": "<YYYY-MM-DD>"}` to `<workspace>/state/naukri.json`.
5. Never change any other field (salary, notice, skills, locations, personal details) unless the
   user asked for that exact change.

## Applying on Naukri (Haiku brief additions)

- Open the job page; if it says "Applied", report `already_applied`.
- "Apply" (Naukri apply) may open a "recruiter questions" chat drawer on the right; answer each from
  `answers.md` (numbers only in numeric boxes; CTC in lakhs). A question not covered: close the
  drawer without submitting and report `needs_you` with the exact text and options.
- "Apply on company site": clicking it makes Naukri log an application at once. So before clicking,
  check the employer is allowed (never-apply list and the services-company rule; small Naukri
  advertisers are often IT services firms: check their website's About page). Then report
  `not_naukri_apply` with the URL, or apply if the site is a simple guest form.
- Success shows "Applied" / "You have successfully applied". Confirm before reporting `applied`.
- Naukri limits daily applies (around 50 is commonly reported). If a limit message appears, stop the
  wave and report it.
- One browser agent at a time: the Naukri wave runs after or before the LinkedIn waves, never with them.
