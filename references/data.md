# Data formats and clusters

## runs/<run>/jobs.json

A JSON list. One object per job; add fields as stages complete.

```json
{
  "title": "AI Engineer",
  "company": "Example Labs",
  "location": "Bengaluru, India (hybrid)",
  "url": "https://job-boards.greenhouse.io/example/jobs/123",
  "source": "google-greenhouse",
  "posted": "2026-11-22",
  "description": "optional raw text from the search result",
  "min_years": 2,
  "location_ok": true,
  "required_skills": ["python", "rag", "langgraph", "aws"],
  "preferred_skills": ["kubernetes", "terraform"],
  "cluster": "AI Engineering",
  "status": "kept",
  "drop_reason": "",
  "score": 82,
  "missing_required": [],
  "missing_preferred": ["kubernetes", "terraform"],
  "resume_file": "resumes/2026-11-22/Akhilender_Reddy_AI_Engineer_ExampleLabs.pdf",
  "note": ""
}
```

`status`: `kept` or `dropped` during filtering; `applied`, `needs_you`, `failed` or `skipped` after
Stage 6. `score`, `missing_required` and `missing_preferred` are written by `jobhunt.py score`.

Write skill names short and consistent ("kubernetes", not "experience with Kubernetes clusters"),
one skill per entry, so the same skill counts as the same thing across postings. Common spelling
variants (k8s, GenAI, Postgres) are merged by the script.

## Clusters

Cluster by what the posting's required skills are mostly about. The title is a hint, not the rule: a
"Software Engineer" posting whose requirements are RAG, agents and evals belongs in AI Engineering.

| Cluster | Required skills are mostly |
|---|---|
| AI Engineering | LLMs, RAG, agents, prompt and eval work, ML frameworks, vector databases |
| AI Security | Securing AI systems or using AI for security: threat modelling, red teaming, guardrails, SIEM, compliance frameworks, network or cloud security |
| Forward Deployed / Solutions | Customer-facing delivery: integrations, rapid prototyping, deployment at client sites, stakeholder work, plus general engineering |
| Software Engineering | Backend, full-stack or product engineering: languages, APIs, databases, system design, testing |
| DevOps / Platform | CI/CD, containers, Kubernetes, infrastructure as code, observability, cloud operations, MLOps |

Use `Other` only when nothing fits, and name a new cluster when four or more postings share a theme
the table lacks.

## runs/<run>/cluster_notes.json

Two or three short, factual points per cluster on what its postings ask for. They appear in the gap
report above the numbers.

```json
{
  "AI Engineering": [
    "Most postings want production RAG plus an evaluation practice, not just prototypes.",
    "Kubernetes and Terraform appear as preferred skills in over half."
  ]
}
```

## state/applied.csv

Columns: `date, company, title, cluster, location, url, source, status, score, resume_file, note`.
A row with a blank title means "already applied at this company before the tracker existed" and
blocks every role at that company; delete the row to lift the block.
