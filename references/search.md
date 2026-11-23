# Search sources

Freshness matters most: only postings inside the chosen window, never results from an earlier run.
The aim is volume (100+ postings scanned a day), so lean on the free direct sources and treat paid
ones as extras. If Apify charges look like exceeding about a dollar a run, stop adding paid sources
and say so.

## Where jobs are listed (the portals)

| Kind | Portals | How the skill reads them |
|---|---|---|
| Company job boards (ATS) | Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Recruitee, Workday | `fetch_boards.py fetch` - public API per board, free, no login |
| Other ATS, no public API used yet | iCIMS, Taleo, SuccessFactors, Oracle Recruiting Cloud, Phenom, Eightfold, BambooHR, Teamtailor, Personio, JazzHR, Zoho Recruit, Keka, Darwinbox | Google past-24h `site:` search, or Chrome on the company careers page |
| Job sites | LinkedIn (public search is in `fetch_boards.py`), Naukri, Indeed, Foundit, Instahyre, Wellfound, Cutshort, Hirist, Glassdoor | Chrome when signed in; Apify actors below |
| Aggregators | Firecrawl `jobs_search`, hirebase, Google Jobs | Optional extras |

## Direct boards: `fetch_boards.py`

```
python <skill>/scripts/fetch_boards.py fetch    <workspace> <run> --days 1
python <skill>/scripts/fetch_boards.py add      <workspace> <ats job urls...>
python <skill>/scripts/fetch_boards.py discover <workspace> --limit 20000
```

- `fetch` reads every board in `boards.json`, keeps postings that are recent, match the role
  keywords and are in India or remote-without-a-region, and stores each with its description, so
  Stage 3 needs no second fetch for them. It prints boards read, open jobs and matches per source.
- `add` learns boards from any ATS job URLs (Greenhouse, Lever, Ashby, SmartRecruiters, Workable,
  Recruitee, Workday). Run it on every ATS link found by any other source.
- `discover` bulk-adds boards from the Common Crawl index. Run it occasionally (monthly is plenty);
  boards that do not exist are dropped automatically on the next fetch.
- Workday rate-limits bursts (HTTP 429); errors are listed and those boards are retried next run.
- Weekends are quiet. If a 24-hour run finds little, say so and offer `--days 3`.

## Chrome for signed-in portals

In the user's Chrome, open the portal's job search with its past-24-hours filter and read result
pages as text (`get_page_text`), paging until results run out or repeat:

- LinkedIn: `https://www.linkedin.com/jobs/search/?keywords=<role>&location=India&f_TPR=r86400&sortBy=DD`
- Naukri: `https://www.naukri.com/<role-with-dashes>-jobs?jobAge=1&experience=2`
- Wellfound, Instahyre, Cutshort: their job search pages, newest first.

If a portal shows a sign-in wall, note it as a blocker for the end-of-run list and move on.

## Paid extras

Use whichever of these tools the session has.

Replace the keywords with the roles the user picked (keywords per role are in `config.json`).
Freshness values below are for "past 24 hours"; widen them when the user picked 3 or 7 days.

## Apify actors (via `call-actor`; fetch the actor's input schema first, schemas change)

| Actor | Good for | Input that worked |
|---|---|---|
| `valig/linkedin-jobs-scraper` | Volume, public LinkedIn listings, no login | `{"keywords":"AI Engineer OR GenAI OR LLM Engineer","location":"India","datePosted":"r86400","limit":150,"urlParam":[{"key":"sortBy","value":"DD"}],"titleExclude":["senior","sr","staff","principal","lead","manager","director","head","intern","vp","vice president","avp","architect"]}` |
| `valig/naukri-jobs-scraper` | India; filters experience at source | `{"keywords":"AI Engineer, Generative AI, LLM, Agentic AI","experience":1,"jobAge":"1","sort":"f","jobPostType":["1"],"limit":300}` |
| `hirebase/remote-jobs` | Company ATS pages; real years filter | `{"jobTitles":["AI Engineer","Forward Deployed Engineer","LLM Engineer","Software Engineer"],"yoeMax":2,"includeJobsWithoutYoe":false,"postedWithinDays":1,"dedupeBy":"companyAndTitle","hideRecruitingAgencies":true,"sortBy":"date_posted","maxResults":200}` |
| `getascraper/india-job-inventory-feed` | Indeed and Foundit in India | `{"sources":["indeed","foundit"],"keyword":"AI Engineer","maxExperienceYears":2,"postedWithinDays":1,"maxItemsPerSource":60,"uniqueOnly":true}` |
| `apify/google-search-scraper` | Career pages on ATS sites | `"quickDateRange":"d1","maxPagesPerQuery":2` with one `site:` query per line (below) |

Known quirks:

- LinkedIn: `datePosted` is `r86400` (24h), `r604800` (7d), `r2592000` (30d). Always pass
  `location: "India"`; with no location it returns US jobs only. Its experience-level filter is
  ignored, so filter years afterwards. The 24h filter leaks reposts; `sortBy=DD` reduces them.
  Listings with no external apply link are low value.
- Naukri: `jobPostType ["1"]` keeps company postings and drops consultancies. Many listings have
  thousands of applicants; `experience: 2` thins them.
- hirebase: has no "open to India" filter. Many results are US-only remote; check eligibility on the
  posting.
- india-job-inventory-feed: Hirist, Instahyre, Wellfound, CutShort and Unstop returned nothing
  useful. Most Indeed rows state no experience, so read the posting.

## Career pages through Google (past 24 hours)

Use the Apify Google actor above, or `firecrawl_search` with `tbs: "qdr:d"` (`qdr:w` for 7 days), or
a normal web search with the past-day filter. Queries, one per ATS and role:

```
site:job-boards.greenhouse.io India "AI engineer"
site:boards.greenhouse.io India "AI engineer"
site:jobs.lever.co "AI engineer" India
site:jobs.ashbyhq.com "forward deployed engineer"
site:jobs.workable.com "AI engineer" India
site:jobs.smartrecruiters.com "AI engineer" India
site:myworkdayjobs.com "AI engineer" India
```

Google's index lags a few hours, so this finds fewer jobs than the boards but they are direct
employer links, which are the best ones to apply through.

## Firecrawl

- `jobs_search`: `{"query":"forward deployed engineer","posted_within_days":1,"limit":50}`; add
  `"location":"India"` for India roles. `boards_only` returns few rows; leave it off.
- `firecrawl_scrape` on a posting with `formats: ["query"]` and `maxAge: 0` is the quickest way to
  pull the experience requirement, location policy and skills from a live page.

## Companies the user never applies to

`config.json` `exclude_companies` (currently Wipro, Infosys, TCS, Cognizant, HCLTech). `jobhunt.py triage`
drops them automatically; never apply to them, even when they arrive by a link the user pastes or
as a repost under another name, such as "Spore N Sprouts" reposting a Cognizant role.

## After searching

- Keep the employer or ATS link when the same job also appears on an aggregator.
- Postings must be live: re-open the apply link before shortlisting.
- Record `source` on every job so weak sources can be dropped later.
