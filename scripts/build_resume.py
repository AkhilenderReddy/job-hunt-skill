"""Render a resume JSON file to a one-column, ATS-readable PDF.

Usage:  python build_resume.py <resume.json> <output.pdf>

Uses headless Chrome or Edge to print HTML to PDF (no Python packages needed). Set CHROME_PATH if
neither is found. The HTML is kept next to the PDF so wording can be checked without opening the PDF.
Text wrapped in **double asterisks** in the JSON is printed bold. Schema: see references/resume.md.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CSS = """
@page { size: A4; margin: 9mm 12mm; }
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 9.6pt; line-height: 1.27; color: #000; margin: 0; }
a { color: #000; text-decoration: none; }
.head { display: flex; justify-content: space-between; align-items: flex-end; }
.head h1 { font-size: 22pt; margin: 0; }
.head .right { text-align: right; }
h2 { font-size: 10.5pt; font-variant: small-caps; font-weight: normal; border-bottom: 1px solid #000;
     margin: 5px 0 2px; padding-bottom: 1px; }
p { margin: 0; }
table.skills { border-collapse: collapse; width: 100%; }
table.skills td { vertical-align: top; padding: 0 0 1px; }
table.skills td.group { font-weight: bold; width: 21%; padding-right: 8px; }
.row { display: flex; justify-content: space-between; gap: 12px; }
.row .strong { font-weight: bold; }
.row.sub { font-style: italic; }
ul { margin: 1px 0 3px; padding-left: 16px; }
li { margin: 0 0 1px; }
"""


def inline(text: str) -> str:
  escaped = html.escape(str(text), quote=False)
  return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def bullets(items: list[str]) -> str:
  return "<ul>" + "".join(f"<li>{inline(item)}</li>" for item in items) + "</ul>" if items else ""


def link(label: str, url: str | None) -> str:
  return f'<a href="{html.escape(url, quote=True)}">{inline(label)}</a>' if url else inline(label)


def render(resume: dict) -> str:
  links = " | ".join(link(item["label"], item.get("url")) for item in resume.get("links", []))
  contact = " | ".join(part for part in (
    f"Email: {link(resume['email'], 'mailto:' + resume['email'])}" if resume.get("email") else "",
    f"Mobile: {inline(resume['mobile'])}" if resume.get("mobile") else "") if part)
  out = [f"<div class='head'><div><h1>{inline(resume['name'])}</h1><div>{links}</div></div>"
         f"<div class='right'><div>Location: {inline(resume.get('location', ''))}</div><div>{contact}</div></div></div>"]
  if resume.get("summary"):
    out.append(f"<h2>Professional Summary</h2><p>{inline(resume['summary'])}</p>")
  if resume.get("skills"):
    rows = "".join(f"<tr><td class='group'>{inline(group['group'])}</td><td>{inline(group['items'])}</td></tr>"
                   for group in resume["skills"])
    out.append(f"<h2>Technical Skills</h2><table class='skills'>{rows}</table>")
  if resume.get("experience"):
    out.append("<h2>Experience</h2>")
    for job in resume["experience"]:
      out.append(f"<div class='row'><span class='strong'>{inline(job['company'])}</span><span>{inline(job.get('dates', ''))}</span></div>"
                 f"<div class='row sub'><span>{inline(job.get('title', ''))}</span><span>{inline(job.get('location', ''))}</span></div>"
                 + bullets(job.get("bullets", [])))
  if resume.get("projects"):
    out.append("<h2>Projects</h2>")
    for project in resume["projects"]:
      right = link(project.get("link_label", ""), project.get("link_url")) if project.get("link_label") else ""
      stack = f"<div class='row sub'><span>Technology Stack: {inline(project['stack'])}</span></div>" if project.get("stack") else ""
      out.append(f"<div class='row'><span class='strong'>{inline(project['name'])}</span><span><i>{right}</i></span></div>"
                 + stack + bullets(project.get("bullets", [])))
  if resume.get("education"):
    out.append("<h2>Education</h2>")
    for school in resume["education"]:
      out.append(f"<div class='row'><span class='strong'>{inline(school['school'])}</span><span>{inline(school.get('location', ''))}</span></div>"
                 f"<div class='row sub'><span>{inline(school.get('degree', ''))}</span><span>{inline(school.get('dates', ''))}</span></div>")
  if resume.get("achievements"):
    out.append(f"<h2>{inline(resume.get('achievements_title', 'Achievements & Certifications'))}</h2>"
               + bullets(resume["achievements"]))
  title = html.escape(f"{resume['name']} - Resume")
  return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{title}</title>"
          f"<style>{CSS}</style></head><body>{''.join(out)}</body></html>")


def find_browser() -> str | None:
  candidates = [
    os.environ.get("CHROME_PATH"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"),
    shutil.which("msedge"), shutil.which("chrome"),
  ]
  return next((path for path in candidates if path and Path(path).exists()), None)


def main(argv: list[str]) -> int:
  if len(argv) != 3:
    print(__doc__)
    return 2
  source, target = Path(argv[1]).resolve(), Path(argv[2]).resolve()
  resume = json.loads(source.read_text(encoding="utf-8"))
  target.parent.mkdir(parents=True, exist_ok=True)
  page = target.with_suffix(".html")
  page.write_text(render(resume), encoding="utf-8")
  browser = find_browser()
  if not browser:
    print(f"No Chrome or Edge found. HTML written to {page}; set CHROME_PATH and rerun.")
    return 1
  profile = target.parent / ".pdf-browser-profile"
  subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                  f"--user-data-dir={profile}", f"--print-to-pdf={target}", page.as_uri()],
                 check=False, capture_output=True, timeout=120)
  shutil.rmtree(profile, ignore_errors=True)
  if not target.exists() or target.stat().st_size < 1000:
    print(f"PDF was not produced. HTML is at {page}.")
    return 1
  pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", target.read_bytes()))
  print(f"wrote {target} ({target.stat().st_size // 1024} KB, {pages or '?'} page(s))")
  if pages > 1:
    print("WARNING: more than one page. Trim the least relevant bullets and rebuild.")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
