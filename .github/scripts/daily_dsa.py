import datetime
import hashlib
import html
import json
import pathlib
import re
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Content-Type": "application/json",
}

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def strip_html(raw):
    text = re.sub(r"<pre[^>]*>", "\n```\n", raw or "")
    text = re.sub(r"</pre>", "\n```\n", text)
    text = re.sub(r"<(br|p|div|li)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(text)).strip()

def fetch_leetcode_daily():
    query = {
        "query": """
        query questionOfToday {
          activeDailyCodingChallengeQuestion {
            date
            link
            question {
              questionFrontendId
              title
              titleSlug
              difficulty
              content
              topicTags { name }
              codeSnippets { langSlug code }
            }
          }
        }
        """
    }
    req = urllib.request.Request(
        "https://leetcode.com/graphql",
        data=json.dumps(query).encode("utf-8"),
        headers=HEADERS,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    item = data["data"]["activeDailyCodingChallengeQuestion"]
    q = item["question"]
    java_code = ""
    for snip in q.get("codeSnippets") or []:
        if snip.get("langSlug") == "java":
            java_code = snip.get("code", "")
            break
    return {
        "source": "LeetCode Daily",
        "id": q["questionFrontendId"],
        "title": q["title"],
        "slug": q["titleSlug"],
        "difficulty": q["difficulty"],
        "tags": [t["name"] for t in (q.get("topicTags") or [])],
        "url": "https://leetcode.com" + item["link"],
        "description": strip_html(q.get("content", "")),
        "java_code": java_code,
    }

def fetch_codeforces_fallback(date_str):
    req = urllib.request.Request(
        "https://codeforces.com/api/problemset.problems",
        headers={"User-Agent": HEADERS["User-Agent"]},
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    problems = [
        p for p in data["result"]["problems"]
        if 800 <= p.get("rating", 0) <= 1500 and p.get("tags")
    ]
    idx = int(hashlib.sha256(date_str.encode()).hexdigest(), 16) % len(problems)
    p = problems[idx]
    cid, pindex = p["contestId"], p["index"]
    title = p["name"]
    return {
        "source": "Codeforces DSA",
        "id": f"{cid}{pindex}",
        "title": title,
        "slug": slugify(f"{cid}-{pindex}-{title}"),
        "difficulty": f"Rating {p.get('rating', 'N/A')}",
        "tags": p.get("tags", []),
        "url": f"https://codeforces.com/problemset/problem/{cid}/{pindex}",
        "description": f"Solve Codeforces problem **{cid}{pindex} - {title}**.\n\nRead the full statement and sample test cases on [Codeforces](https://codeforces.com/problemset/problem/{cid}/{pindex}).",
        "java_code": "",
    }

def main():
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    year, month, _ = today.split("-")
    try:
        problem = fetch_leetcode_daily()
    except Exception:
        problem = fetch_codeforces_fallback(today)

    folder = pathlib.Path("daily-dsa") / year / month / f"{today}-{problem['slug']}"
    folder.mkdir(parents=True, exist_ok=True)
    tags_str = ", ".join(problem["tags"]) if problem["tags"] else "Algorithms"

    readme_content = f"""# {problem['id']}. {problem['title']}

- **Date:** {today}
- **Source:** [{problem['source']}]({problem['url']})
- **Difficulty:** {problem['difficulty']}
- **Topics:** {tags_str}

## Problem Statement

{problem['description']}

## Approach & Complexity

- **Approach:** TODO - document key intuition and edge cases
- **Time Complexity:** `O(...)`
- **Space Complexity:** `O(...)`
"""
    (folder / "README.md").write_text(readme_content, encoding="utf-8")

    starter = problem["java_code"].strip()
    if not starter:
        starter = (
            "import java.io.*;\n"
            "import java.util.*;\n\n"
            "public class Solution {\n"
            "    public static void main(String[] args) throws Exception {\n"
            "        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));\n"
            "        // TODO: Implement solution\n"
            "    }\n"
            "}\n"
        )
    java_content = (
        f"/**\n"
        f" * {problem['source']} ({today})\n"
        f" * Problem: {problem['id']}. {problem['title']}\n"
        f" * Difficulty: {problem['difficulty']}\n"
        f" * Topics: {tags_str}\n"
        f" * URL: {problem['url']}\n"
        f" */\n\n"
        f"{starter}\n"
    )
    (folder / "Solution.java").write_text(java_content, encoding="utf-8")

    index_path = pathlib.Path("daily-dsa") / "INDEX.md"
    header = "# Daily DSA & Java Practice Log\n\n| Date | Problem | Difficulty | Topics | Files |\n| :--- | :--- | :--- | :--- | :--- |\n"
    rel_dir = f"{year}/{month}/{today}-{problem['slug']}"
    row = f"| {today} | [{problem['id']}. {problem['title']}]({problem['url']}) | {problem['difficulty']} | {tags_str} | [README]({rel_dir}/README.md) · [Solution.java]({rel_dir}/Solution.java) |"

    existing_rows = []
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| 20") and not line.startswith(f"| {today} |"):
                existing_rows.append(line)
    index_path.write_text(header + "\n".join([row] + existing_rows) + "\n", encoding="utf-8")

    msg = f"feat(dsa): add {today} {problem['title']} ({problem['difficulty']})"
    pathlib.Path(".commit_msg.txt").write_text(msg, encoding="utf-8")
    print(msg)

if __name__ == "__main__":
    main()
