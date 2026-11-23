# Tailoring a resume

Source of truth: `profile/master_resume.json`. A tailored resume is a one-page cut of it, saved as
`resumes/<run>/<First>_<Last>_<Role>_<Company>.json` and built with:

```
python <skill>/scripts/build_resume.py <resume.json> <resume.pdf>
```

The script prints the page count. If it is over one page, trim the least relevant bullets and
rebuild; do not shrink the font.

## What to change per job

1. **Summary** (2 to 3 lines): who the user is in this job's terms, using the posting's own words
   for things the user has really done.
2. **Skills**: regroup and reorder so the posting's required skills come first. Use the posting's
   spelling of a skill the user has ("vector database" next to Qdrant, "REST APIs" for FastAPI
   work). Leave out skills irrelevant to this job to save space.
3. **Experience bullets**: lead with the bullets closest to the job. Keep every number and name
   exactly as in the master. Rewording for the posting's vocabulary is fine; changing what happened
   is not.
4. **Projects and achievements**: keep those that support this cluster; drop the rest if space is
   short.

## What never changes

Employers, titles, dates, education, numbers, and the set of skills. If the posting wants something
that is not in the master resume, it does not go on the resume. Record it as a missing skill; that
is what the gap report is for.

## Resume JSON schema

`**double asterisks**` print as bold.

```json
{
  "name": "", "location": "", "email": "", "mobile": "",
  "links": [{"label": "LinkedIn", "url": "https://..."}],
  "summary": "",
  "skills": [{"group": "Applied AI", "items": "LLMs, RAG, ..."}],
  "experience": [{"company": "", "title": "", "dates": "", "location": "", "bullets": ["..."]}],
  "projects": [{"name": "", "link_label": "GitHub Link", "link_url": "", "stack": "", "bullets": ["..."]}],
  "education": [{"school": "", "degree": "", "dates": "", "location": ""}],
  "achievements_title": "Achievements & Certifications",
  "achievements": ["..."]
}
```

## Checks before using the PDF

- One page, text selectable (it is, when built by the script).
- File name carries the user's name, the role and the company, with no spaces.
- Read the HTML once for anything that is not in the master resume.
