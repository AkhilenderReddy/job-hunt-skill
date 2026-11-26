# Applying

Apply on the employer's own page or ATS, not through an aggregator or Easy Apply, and soon after the
posting appears.

## Tools

Use the browser the session has, in this order of preference:

1. **Claude in Chrome** (the browser extension): the user's own Chrome with their sign-ins. Use its
   file-upload tool to attach the tailored PDF from `resumes/<run>/`.
2. **Computer use**: when a file picker or a control the extension cannot reach is needed.
3. **Built-in browser**: for reading postings and for simple forms.

Work in a new tab per job. Read pages as text where possible; screenshots only when layout matters.

## Steps for one application

1. Open the apply link. Confirm the posting is still open and is the job that was shortlisted.
2. Decline optional cookies. Reach the form (an "Apply" button may open a second page or an ATS).
3. Upload the resume first: many forms prefill from it. Then check the file name shows on the page.
   A consent dialog or a form re-render can silently drop the upload; re-upload if it is gone.
4. Fill every field from `profile/profile.json` and `profile/answers.md`. Copy email and phone
   exactly. Fix anything the prefill got wrong (dates, current-employer tick box, phone country).
5. Tick required consents (privacy notice, terms, data processing, GDPR). Leave marketing, SMS and
   talent-community opt-ins unticked.
6. On multi-step forms, wait for the next step to load before filling; some take ten seconds.
7. Before submitting, scan for empty required fields and validation errors.
8. Submit, then confirm it went through: a thank-you page, a "submitted" message, or a confirmation
   email. No confirmation means the status is `failed`, not `applied`.

## Order of work

1. Applications on direct ATS pages that need no login (Greenhouse, Lever, Ashby, Workable,
   SmartRecruiters, most company forms).
2. Sites where the user is already signed in in Chrome (LinkedIn, Naukri, a Workday tenant).
3. Everything else goes on the blocker list, grouped by site, so one sign-in from the user unlocks
   several applications. After they say they have signed in, finish those.

## When to stop and mark `needs_you`

- A login, a new account, a password or a one-time code. The user signs in themselves; if they are
  already signed in, carry on. Typing passwords, creating accounts and fetching verification codes
  from the user's mailbox stay with the user: list the site and they do that step.
- A captcha or "I'm not a robot" check. Leave these for the user; do not attempt or route around
  them.
- A required question that `answers.md` does not cover.
- A legal or ethics declaration (non-compete or NDA, conflicts of interest, relatives at the
  company, government roles, criminal history, export-control citizenship) that is not already
  confirmed in `answers.md`.
- An assessment, video answer or cover letter that needs the user's own input.

Write in `note` exactly what is needed and leave the tab open when that helps the user finish.
Then move to the next job.

## Things that have gone wrong before

- **Greenhouse**: the GDPR "process my data" box is required and easy to miss; the separate
  "retain my data" box is optional.
- **Phenom career sites** (for example HPE): multi-step. An unanswered optional "preferred name"
  question blocks Next. "I currently work here" may not tick on the first click; verify it, or the
  end date is wrong.
- **Eightfold career sites** (for example Ascendion): a consent dialog appears over the form and
  must be accepted before the upload registers.
- **Workday**: needs an account per employer, so it is `needs_you` unless already signed in.
- **Chat widgets and cookie bars** can cover the Next or Submit button; close or scroll past them.
- **Custom dropdowns** (not a normal select): click to open, then pick the option by its text.
- **Contact or "talk to us" forms** on a careers page are not application forms; do not fill them.
- **Salary fields**: follow `answers.md` (text if allowed, the stated number if a number is forced).

## Google Forms

- Open the form as the user's application account by adding `?authuser=<email>` to the viewform URL.
- The file-upload question opens Google's cross-origin "Insert file" picker, which browser tools cannot
  fill. Fill every other field, leave the tab open, and list it for the user: "Add File, then Submit".
- A numeric box whose validation range excludes the user's true value (for example CTC 10-100 lakhs) is
  filled with the true value anyway and flagged; never raise a number to pass validation.


## Form classes and which model applies (cheapest that works)

Classify each job by its apply URL before a wave, then send it to the matching agent. Escalate only
on failure: Haiku `stuck` -> next Sonnet wave; Sonnet `needs_you`/`needs_signin` -> the user list.

| Class | Sites (apply URL contains) | Why | Model |
|---|---|---|---|
| A. Easy, single guest form | LinkedIn Easy Apply; Greenhouse (`greenhouse.io`, `grnh.se`); Lever (`jobs.lever.co`); Ashby (`jobs.ashbyhq.com`); Workable (`apply.workable.com`, `jobs.workable.com`); SmartRecruiters (`jobs.smartrecruiters.com`); Recruitee; Breezy (`breezy.hr`); JazzHR (`applytojob.com`); Teamtailor; Personio (`jobs.personio`); BambooHR (`bamboohr.com`, may show a captcha) | One page or a short wizard, standard fields, normal file input, no account | Haiku |
| B. Guided or quirky, still no account | Phenom-based career sites (`/global/en/job/`, froze on HPE and Marsh), Eightfold (`eightfold.ai`), Avature (`avature`), PeopleStrong, Darwinbox, Keka, Zoho Recruit (image captcha seen), Oracle Recruiting Cloud (`oraclecloud.com`, may end in an email code), RippleHire, TurboHire, Kula, Hirist/Cutshort, company-built forms | Multi-step, custom widgets, dropdown searches, occasional code screens | Sonnet |
| C. Fill only, user finishes | Google Forms (`docs.google.com/forms`, `forms.gle`): file picker unreachable; iCIMS (`icims.com`): form in a cross-origin frame | Tools cannot complete the last step | Haiku fills (Google Forms), the user uploads + submits; iCIMS straight to the user |
| D. Account or login first | Workday (`myworkdayjobs.com`, `myworkdaysite.com`), Taleo (`taleo.net`), SuccessFactors (`sapsf`, `career55`, `jobs.sap.com` sign-in), contactHR (`contacthr.com`), Amazon.jobs, IBM, Accenture, Google Careers (needs the right Google account) | Needs an account, password, MFA or email code | No model: straight to the user's blocker list; an agent continues only after they sign in |

Cheap pre-check for class A: Firecrawl's Alexandria providers (`greenhouse-io jobs/job`,
`ashbyhq-com jobs/job`, `workable jobs/employer_job`) return a posting's application questions
without opening a browser. When available, list them first and ask the user any question missing
from `answers.md` before the wave, so Haiku never stops mid-form.
