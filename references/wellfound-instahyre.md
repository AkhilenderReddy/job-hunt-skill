# Wellfound and Instahyre flows (daily)

Both portals keep one candidate profile; applying is a click (Instahyre) or a click plus a short note
(Wellfound). Search runs through Apify (no model); the browser is only for upkeep and applying.

| # | Step | Wellfound | Instahyre | Model |
|---|---|---|---|---|
| 1 | Profile upkeep | Weekly (`state/wellfound.json` `last_profile_check`): status "actively looking", latest main resume, roles, India + remote preferences. | Daily (`state/instahyre.json` `last_refresh`): open the profile, re-upload the run's main resume, re-save; confirm the updated date. | Haiku |
| 2 | Search | Apify `memo23/wellfound-jobs-scraper` (fetch its input schema first): roles from `config.json`, location India, also `remoteOnly`, newest first, about 100 items. Save items as `runs/<run>/apify_wellfound.json`. | Apify `getascraper/instahyre-jobs-scraper`: job functions for engineering / AI / DevOps, `locations` Bengaluru, Hyderabad, Pune (+ remote), `excludeAgencyPosted: true`, `includeDetails: true`, about 100 items. Save as `runs/<run>/apify_instahyre.json`. | No model |
| 3 | Merge, triage, read, score | `merge_extra.py`, then the normal Stage 2-3 pipeline (never-apply list and services rule; experience limit; cross-source duplicates dropped). | same | Scripts + Haiku |
| 4 | Note | Wellfound asks for a note to the hiring team: write it in the approved YC note style (`answers.md`), all notes in one batch. | none | Sonnet (Wellfound only) |
| 5 | Apply | Signed-in Chrome: job page -> Apply -> paste the note -> Send; confirm "Applied". | Signed-in Chrome: job page -> "Apply" / "Interested"; answer any short question from `answers.md`; confirm. | Haiku |
| 6 | Inbox | - | Instahyre "Opportunities" (recruiter invites): accept those that pass the never-apply list, services rule, location and experience limit; decline nothing; list the rest for the user. | Haiku |
| 7 | Track | `source: wellfound` | `source: instahyre` | No model |

A sign-in page on either site is a blocker for the user; never type a password or request a code.
Wellfound applications go out under the user's name with a note: never send one that claims anything
beyond `master_resume.json`.
