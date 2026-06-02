#!/usr/bin/env python3
"""Sync your accepted LeetCode submissions into this repo.

Usage:
    python sync.py                 # incremental sync (stops at first already-synced submission)
    python sync.py --full          # re-scan your entire submission history
    python sync.py --limit 50      # only look at the 50 most recent submissions
    python sync.py --push          # git add/commit/push after syncing
    python sync.py --dry-run       # show what would happen, write nothing

Auth is via your browser session cookie. Copy .env.example to .env and fill it in.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # dotenv is optional; env vars still work without it
    pass

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "data" / "state.json"

# LeetCode language name -> file extension. Covers every language LC currently offers.
LANG_EXT = {
    "python": "py", "python3": "py", "pythondata": "py",
    "c": "c", "cpp": "cpp", "c++": "cpp",
    "java": "java", "csharp": "cs", "c#": "cs",
    "javascript": "js", "typescript": "ts",
    "php": "php", "swift": "swift", "kotlin": "kt",
    "dart": "dart", "golang": "go", "go": "go",
    "ruby": "rb", "scala": "scala", "rust": "rs",
    "racket": "rkt", "erlang": "erl", "elixir": "ex",
    "mysql": "sql", "mssql": "sql", "oraclesql": "sql", "postgresql": "sql",
    "bash": "sh",
}

SUBMISSION_DETAILS_QUERY = """
query submissionDetails($submissionId: Int!) {
  submissionDetails(submissionId: $submissionId) {
    runtime
    runtimeDisplay
    runtimePercentile
    memory
    memoryDisplay
    memoryPercentile
    code
    timestamp
    statusCode
    lang { name verboseName }
    question { questionId titleSlug title }
    topicTags { name slug }
    notes
  }
}
"""


class LeetCodeClient:
    def __init__(self, session_cookie: str, csrftoken: str, domain: str = "leetcode.com"):
        self.domain = domain
        self.base = f"https://{domain}"
        self.session = requests.Session()
        self.session.cookies.set("LEETCODE_SESSION", session_cookie, domain=domain)
        self.session.cookies.set("csrftoken", csrftoken, domain=domain)
        self.session.headers.update({
            "x-csrftoken": csrftoken,
            "Referer": self.base + "/",
            "Origin": self.base,
            "User-Agent": "lcSync/1.0 (+https://github.com)",
            "Content-Type": "application/json",
        })

    def list_submissions(self, offset: int, limit: int) -> dict:
        """Page through the REST submissions dump (newest-first)."""
        url = f"{self.base}/api/submissions/"
        resp = self.session.get(url, params={"offset": offset, "limit": limit}, timeout=30)
        if resp.status_code == 403:
            raise SystemExit(
                "403 from LeetCode. Your LEETCODE_SESSION cookie is likely expired or wrong. "
                "Log in again and copy a fresh cookie into .env."
            )
        resp.raise_for_status()
        return resp.json()

    def submission_details(self, submission_id: int) -> dict | None:
        url = f"{self.base}/graphql/"
        payload = {
            "operationName": "submissionDetails",
            "query": SUBMISSION_DETAILS_QUERY,
            "variables": {"submissionId": int(submission_id)},
        }
        resp = self.session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return data.get("submissionDetails")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"synced": {}}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def ext_for_lang(lang: str) -> str:
    return LANG_EXT.get(lang.lower(), "txt")


def iter_accepted(client: LeetCodeClient, state: dict, full: bool, limit: int | None):
    """Yield accepted submissions newest-first, stopping early on incremental runs."""
    synced = state["synced"]
    page = 20
    offset = 0
    seen = 0
    while True:
        data = client.list_submissions(offset, page)
        dump = data.get("submissions_dump", [])
        if not dump:
            break
        for sub in dump:
            seen += 1
            if limit is not None and seen > limit:
                return
            if sub.get("status_display") != "Accepted":
                continue
            sid = str(sub["id"])
            if not full and sid in synced:
                # Newest-first: once we hit a known submission, everything older is synced.
                return
            yield sub
        if not data.get("has_next"):
            break
        offset += page
        time.sleep(0.7)  # be polite


def write_solution(sub: dict, details: dict, solutions_dir: Path, dry_run: bool) -> Path:
    question = details["question"]
    slug = question["titleSlug"]
    title = question.get("title") or sub.get("title") or slug
    qid = question.get("questionId", "")
    lang = details["lang"]["name"]
    ext = ext_for_lang(lang)

    problem_dir = solutions_dir / slug
    code_path = problem_dir / f"{slug}.{ext}"
    ts = datetime.fromtimestamp(details["timestamp"], tz=timezone.utc).strftime("%Y-%m-%d")

    code = details["code"]
    header = _comment_header(ext, title, qid, slug, client_domain_url(slug), details, ts)
    contents = header + code.rstrip() + "\n"

    if not dry_run:
        problem_dir.mkdir(parents=True, exist_ok=True)
        code_path.write_text(contents, encoding="utf-8", newline="\n")
        _write_problem_readme(problem_dir, title, qid, slug, details, ts)

    return code_path


def client_domain_url(slug: str) -> str:
    return f"https://leetcode.com/problems/{slug}/"


def _comment_header(ext: str, title: str, qid: str, slug: str, url: str, details: dict, ts: str) -> str:
    line1 = f"{qid}. {title}".strip(". ")
    rt = details.get("runtimeDisplay")
    mem = details.get("memoryDisplay")
    rp = details.get("runtimePercentile")
    mp = details.get("memoryPercentile")
    stats = f"Runtime {rt} (beats {rp:.1f}%) | Memory {mem} (beats {mp:.1f}%)" \
        if rp is not None and mp is not None else ""
    body = [line1, url, f"Accepted {ts}"]
    if stats:
        body.append(stats)

    if ext in {"py", "rb", "sh"}:
        return "".join(f"# {ln}\n" for ln in body) + "\n"
    if ext == "sql":
        return "".join(f"-- {ln}\n" for ln in body) + "\n"
    # C-family / most others use block comments
    return "/*\n" + "".join(f" * {ln}\n" for ln in body) + " */\n\n"


def _write_problem_readme(problem_dir: Path, title: str, qid: str, slug: str, details: dict, ts: str) -> None:
    rt = details.get("runtimeDisplay")
    mem = details.get("memoryDisplay")
    rp = details.get("runtimePercentile")
    mp = details.get("memoryPercentile")
    tags = ", ".join(t["name"] for t in (details.get("topicTags") or [])) or "—"
    lines = [
        f"# {qid}. {title}".rstrip(". "),
        "",
        f"- **Problem:** {client_domain_url(slug)}",
        f"- **Language:** {details['lang']['verboseName']}",
        f"- **Accepted:** {ts}",
    ]
    if rp is not None:
        lines.append(f"- **Runtime:** {rt} (beats {rp:.1f}%)")
    if mp is not None:
        lines.append(f"- **Memory:** {mem} (beats {mp:.1f}%)")
    lines.append(f"- **Topics:** {tags}")
    lines.append("")
    (problem_dir / "README.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


EXT_DISPLAY = {
    "py": "Python", "c": "C", "cpp": "C++", "java": "Java", "cs": "C#",
    "js": "JavaScript", "ts": "TypeScript", "php": "PHP", "swift": "Swift",
    "kt": "Kotlin", "dart": "Dart", "go": "Go", "rb": "Ruby", "scala": "Scala",
    "rs": "Rust", "rkt": "Racket", "erl": "Erlang", "ex": "Elixir",
    "sql": "SQL", "sh": "Bash",
}

INDEX_PREAMBLE = """# LeetCode Solutions

My LeetCode solutions, auto-synced from my submissions by [lcSync](sync.py).

To set up and run the sync yourself, see the steps below.

<details>
<summary><b>Usage</b></summary>

```bash
pip install -r requirements.txt
cp .env.example .env          # then paste in your LEETCODE_SESSION + csrftoken cookies
python sync.py                # incremental sync
python sync.py --full         # re-scan entire history
python sync.py --push         # sync, then commit & push
```
</details>
"""


def _parse_problem(problem_dir: Path) -> dict | None:
    """Read a problem's metadata from its generated files for the index."""
    slug = problem_dir.name
    code_files = [p for p in problem_dir.glob(f"{slug}.*") if p.suffix != ".md"]
    if not code_files:
        return None
    langs = sorted({EXT_DISPLAY.get(p.suffix.lstrip("."), p.suffix.lstrip(".").upper())
                    for p in code_files})

    qid, title, accepted = "", slug, ""
    readme = problem_dir / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                heading = line[2:].strip()
                qid, _, rest = heading.partition(". ")
                if rest:
                    title = rest
                else:
                    qid, title = "", heading
            elif "**Accepted:**" in line:
                accepted = line.split("**Accepted:**", 1)[1].strip()
    try:
        sort_key = int(qid)
    except ValueError:
        sort_key = 1 << 30  # non-numeric ids sort last
    return {"slug": slug, "qid": qid, "title": title,
            "langs": ", ".join(langs), "accepted": accepted, "sort_key": sort_key}


def write_index(solutions_dir: Path, dry_run: bool) -> None:
    if not solutions_dir.exists():
        return
    problems = [p for d in sorted(solutions_dir.iterdir()) if d.is_dir()
                for p in [_parse_problem(d)] if p]
    problems.sort(key=lambda p: (p["sort_key"], p["title"]))

    lines = [INDEX_PREAMBLE,
             f"**{len(problems)} solutions** · last updated {datetime.now():%Y-%m-%d}",
             "", "## Solutions", "",
             "| # | Problem | Language(s) | Accepted |",
             "|---|---------|-------------|----------|"]
    for p in problems:
        num = p["qid"] or "—"
        lines.append(f"| {num} | [{p['title']}](solutions/{p['slug']}/) "
                     f"| {p['langs']} | {p['accepted']} |")
    content = "\n".join(lines) + "\n"

    if dry_run:
        print(f"[dry-run] would write README.md index ({len(problems)} problems)")
        return
    (ROOT / "README.md").write_text(content, encoding="utf-8", newline="\n")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def maybe_push(dry_run: bool) -> None:
    if dry_run:
        print("[dry-run] would git add/commit/push")
        return
    if not (ROOT / ".git").exists():
        print("Not a git repo yet. Run 'git init' and add a remote, then re-run with --push.")
        return
    git("add", "-A")  # respects .gitignore (.env and data/state.json stay out)
    staged = git("diff", "--cached", "--name-only").stdout.split()
    if not staged:
        print("Nothing new to commit.")
        return
    msg = f"Sync {len(staged)} LeetCode file(s) — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    commit = git("commit", "-m", msg)
    if commit.returncode != 0:
        print("git commit failed:\n" + commit.stderr)
        return
    print(f"Committed: {msg}")

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
    push = git("push", "-u", "origin", branch)
    if push.returncode != 0:
        print("git push failed:\n" + push.stderr)
    else:
        print("Pushed to remote.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync LeetCode submissions to this repo.")
    parser.add_argument("--full", action="store_true", help="re-scan entire history, not just new")
    parser.add_argument("--limit", type=int, default=None, help="only inspect N most recent submissions")
    parser.add_argument("--push", action="store_true", help="git commit & push after syncing")
    parser.add_argument("--dry-run", action="store_true", help="don't write files or touch git")
    args = parser.parse_args()

    # .strip() + BOM removal: cookies pasted via editors or piped through some
    # shells can pick up surrounding whitespace or a UTF-8 BOM, which breaks the
    # latin-1-only HTTP header encoding.
    session_cookie = (os.getenv("LEETCODE_SESSION") or "").strip().lstrip("﻿")
    csrftoken = (os.getenv("LEETCODE_CSRFTOKEN") or "").strip().lstrip("﻿")
    domain = os.getenv("LEETCODE_DOMAIN", "leetcode.com")
    solutions_dir = ROOT / os.getenv("SOLUTIONS_DIR", "solutions")

    if not session_cookie or not csrftoken:
        print("Missing credentials. Copy .env.example to .env and fill in LEETCODE_SESSION "
              "and LEETCODE_CSRFTOKEN.", file=sys.stderr)
        return 1

    client = LeetCodeClient(session_cookie, csrftoken, domain)
    state = load_state()

    new_count = 0
    processed_ids: set[str] = set()
    written_keys: set[tuple] = set()
    try:
        for sub in iter_accepted(client, state, args.full, args.limit):
            sid = str(sub["id"])
            if sid in processed_ids:  # guard against paginated duplicates
                continue
            processed_ids.add(sid)

            # Submissions arrive newest-first, so the first time we see a given
            # (problem, language) is the latest accepted version. Skip older
            # duplicates — otherwise an older submission overwrites newer code.
            key = (sub.get("title_slug"), sub.get("lang"))
            if key in written_keys:
                state["synced"][sid] = {
                    "slug": sub.get("title_slug"),
                    "lang": sub.get("lang"),
                    "timestamp": sub.get("timestamp"),
                    "superseded": True,
                }
                continue

            details = client.submission_details(sub["id"])
            time.sleep(0.7)  # be polite to the GraphQL endpoint
            if not details or not details.get("code"):
                print(f"  ! skipped {sid} ({sub.get('title')}): no code returned")
                continue

            path = write_solution(sub, details, solutions_dir, args.dry_run)
            slug = details["question"]["titleSlug"]
            lang = details["lang"]["name"]
            written_keys.add(key)
            print(f"  + {slug} [{lang}] -> {path.relative_to(ROOT)}")

            state["synced"][sid] = {
                "slug": slug,
                "lang": lang,
                "timestamp": details["timestamp"],
            }
            new_count += 1
    except KeyboardInterrupt:
        print("\nInterrupted — saving progress so far.")
    finally:
        if not args.dry_run and new_count:
            save_state(state)

    print(f"\nDone. {new_count} new submission(s) synced.")
    write_index(solutions_dir, args.dry_run)
    if args.push:
        maybe_push(args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
