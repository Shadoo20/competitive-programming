#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
from pathlib import Path

import requests


DEFAULT_CACHE = ".cf_sync/solved.json"
DEFAULT_OUTPUT = "codeforces"


def fetch_codeforces_solved(handle: str, count: int = 5000):
    url = "https://codeforces.com/api/user.status"
    params = {"handle": handle, "from": 1, "count": count}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "OK":
        raise RuntimeError(f"Codeforces API error: {payload}")

    solved = {}
    for item in payload.get("result", []):
        verdict = item.get("verdict")
        if verdict != "OK":
            continue

        problem = item.get("problem", {})
        contest_id = problem.get("contestId")
        index = problem.get("index")
        name = problem.get("name", "")

        if contest_id is None or index is None:
            continue

        key = f"{contest_id}-{index}"
        solved[key] = {
            "contestId": contest_id,
            "index": index,
            "name": name,
            "url": f"https://codeforces.com/contest/{contest_id}/problem/{index}",
        }

    return solved


def load_cache(path: Path):
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_cache(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip())
    return value.strip("_") or "problem"


def build_markdown(problem):
    name = problem["name"]
    contest_id = problem["contestId"]
    index = problem["index"]
    slug = safe_slug(name)
    return (
        f"# {contest_id}{index} - {name}\n\n"
        f"- Contest: {contest_id}\n"
        f"- Index: {index}\n"
        f"- Link: {problem['url']}\n\n"
        f"## Solution\n\n"
        "```cpp\n"
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n\n"
        "int main() {\n"
        "    ios::sync_with_stdio(false);\n"
        "    cin.tie(nullptr);\n"
        "\n"
        "    return 0;\n"
        "}\n"
        "```\n"
    )


def github_api(path: str, repo: str, token: str, method: str, data=None):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.request(method, url, headers=headers, json=data, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub API failed for {path}: {response.status_code} {response.text}")
    return response.json()


def create_or_update_github_file(repo: str, token: str, path: str, content: str, message: str, branch: str = "main"):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    existing = requests.get(url, headers=headers, timeout=30)
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": branch,
    }

    if existing.status_code == 200:
        payload["sha"] = existing.json().get("sha")

    response = requests.put(url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(f"Failed to update GitHub file {path}: {response.status_code} {response.text}")
    return response.json()


def sync(handle: str, repo: str, token: str, branch: str, dry_run: bool, cache_file: Path, output_dir: str):
    solved = fetch_codeforces_solved(handle)
    cache = load_cache(cache_file)
    new_entries = {key: info for key, info in solved.items() if key not in cache}

    if not new_entries:
        print("No new Codeforces problems found.")
        return 0

    print(f"Found {len(new_entries)} new problem(s) to add.")

    for key, info in new_entries.items():
        contest_id = info["contestId"]
        index = info["index"]
        name = info["name"]
        slug = safe_slug(name)
        relative_dir = Path(output_dir) / str(contest_id)
        relative_file = relative_dir / f"{contest_id}_{index}_{slug}.md"
        content = build_markdown(info)

        if dry_run:
            print(f"[dry-run] Would create: {relative_file}")
            continue

        relative_file.parent.mkdir(parents=True, exist_ok=True)
        create_or_update_github_file(repo, token, str(relative_file), content, f"Add Codeforces problem {contest_id}{index} - {name}", branch=branch)

    cache.update(solved)
    if not dry_run:
        save_cache(cache_file, cache)
        create_or_update_github_file(
            repo,
            token,
            str(cache_file),
            json.dumps(cache, ensure_ascii=False, indent=2),
            "Update Codeforces solved cache",
            branch=branch,
        )

    return len(new_entries)


def main():
    parser = argparse.ArgumentParser(description="Sync solved Codeforces problems into a GitHub repo.")
    parser.add_argument("--handle", required=True, help="Codeforces handle")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/name format")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token (or set GITHUB_TOKEN)")
    parser.add_argument("--branch", default="main", help="Target GitHub branch")
    parser.add_argument("--cache-file", default=DEFAULT_CACHE, help="Local JSON cache path")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT, help="Folder inside the repo for Codeforces problems")
    parser.add_argument("--dry-run", action="store_true", help="Only preview new problems")
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("Missing GitHub token. Provide --token or set GITHUB_TOKEN.")

    cache_path = Path(args.cache_file)
    count = sync(
        handle=args.handle,
        repo=args.repo,
        token=args.token,
        branch=args.branch,
        dry_run=args.dry_run,
        cache_file=cache_path,
        output_dir=args.output_dir,
    )
    print(f"Completed: {count} new item(s) processed.")


if __name__ == "__main__":
    main()
