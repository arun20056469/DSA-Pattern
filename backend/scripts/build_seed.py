"""Expand patterns_seed.json with verified LeetCode problems.

Fetches the public LeetCode catalog, keeps every existing problem slug stable,
and appends enough tag-matched problems to give each pattern 20 problems.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "backend" / "app" / "seed" / "patterns_seed.json"
CACHE = Path(__file__).resolve().parent / "leetcode_catalog.json"

TAG_MAP = {
    "arrays-hashing": ["array", "hash-table"],
    "two-pointers": ["two-pointers"],
    "sliding-window": ["sliding-window"],
    "stacks-queues-fundamentals": ["stack", "queue"],
    "linked-list-fundamentals": ["linked-list"],
    "fast-slow-pointers": ["linked-list", "two-pointers"],
    "binary-search": ["binary-search"],
    "merge-intervals": ["interval"],
    "monotonic-stack-queue": ["monotonic-stack"],
    "trie": ["trie"],
    "dfs-bfs-trees-graphs": ["tree", "depth-first-search", "breadth-first-search"],
    "backtracking": ["backtracking"],
    "union-find": ["union-find"],
    "graphs-advanced": ["graph", "shortest-path", "topological-sort"],
    "heaps-top-k": ["heap-priority-queue"],
    "greedy": ["greedy"],
    "bit-manipulation": ["bit-manipulation"],
    "dynamic-programming-1d": ["dynamic-programming"],
    "dynamic-programming-2d": ["dynamic-programming", "matrix"],
    "math-number-theory": ["math"],
    "design-data-structures": ["design", "data-structure"],
}

TARGET_PER_PATTERN = 20
QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(categorySlug: $categorySlug limit: $limit skip: $skip filters: $filters) {
    total: totalNum
    questions: data {
      questionId
      title
      titleSlug
      difficulty
      topicTags { slug }
    }
  }
}
"""


def fetch_catalog() -> list[dict]:
    questions: list[dict] = []
    skip = 0
    page_size = 100

    if CACHE.exists():
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
        if cached and len(cached) % page_size == 0:
            questions = cached
            skip = len(cached)

    while True:
        payload = {
            "query": QUERY,
            "variables": {
                "categorySlug": "",
                "limit": page_size,
                "skip": skip,
                "filters": {},
            },
        }
        req = urllib.request.Request(
            "https://leetcode.com/graphql",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Origin": "https://leetcode.com",
                "Referer": "https://leetcode.com/problemset/",
            },
        )

        result = None
        for attempt in range(6):
            try:
                timeout = 30 + attempt * 15
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode())
                result = body["data"]["problemsetQuestionList"]
                break
            except Exception as exc:  # network/read timeout, transient 5xx, etc.
                if attempt == 5:
                    raise RuntimeError(
                        f"Failed to fetch LeetCode page at skip={skip}: {exc}"
                    ) from exc
                time.sleep(1 + attempt)

        page = result["questions"]
        questions.extend(page)
        total = result["total"]
        skip += page_size

        # Persist after every complete page so a later failure can resume.
        if len(questions) % page_size == 0:
            CACHE.write_text(json.dumps(questions, indent=1), encoding="utf-8")

        if not page or skip >= total:
            break

    CACHE.write_text(json.dumps(questions, indent=1), encoding="utf-8")
    return questions


def stage_for(order: int) -> str:
    if order <= 7:
        return "Basic"
    if order <= 14:
        return "Intermediate"
    return "Advanced"


def slug_from_url(url: str) -> str | None:
    match = re.search(r"/problems/([^/?]+)", url)
    return match.group(1) if match else None


def main() -> None:
    catalog = fetch_catalog()
    by_slug = {q["titleSlug"]: q for q in catalog}
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    patterns = seed["patterns"]

    existing_slugs = {
        p["slug"] for pattern in patterns for p in pattern.get("problems", [])
    }
    # Existing LC slugs are already used; don't add them again anywhere.
    used_lc = set()
    for pattern in patterns:
        for problem in pattern.get("problems", []):
            lc = problem.get("leetcode_slug") or slug_from_url(problem["leetcode_url"])
            if lc:
                used_lc.add(lc)

    diff_rank = {"Easy": 0, "Medium": 1, "Hard": 2}

    for pattern in patterns:
        pattern["stage"] = stage_for(pattern["order"])
        current = pattern.setdefault("problems", [])
        existing_count = len(current)

        # Enrich existing entries with verified catalog metadata.
        for problem in current:
            lc = problem.get("leetcode_slug") or slug_from_url(problem["leetcode_url"])
            problem["leetcode_slug"] = lc
            info = by_slug.get(lc) if lc else None
            if info:
                problem["leetcode_id"] = int(info["questionId"])
                problem["tags"] = [t["slug"] for t in info["topicTags"]]
            else:
                problem.setdefault("leetcode_id", None)
                problem.setdefault("tags", [])
            if lc:
                used_lc.add(lc)

        needed = TARGET_PER_PATTERN - existing_count
        if needed <= 0:
            continue

        tags = set(TAG_MAP.get(pattern["slug"], []))
        candidates = [
            q
            for q in catalog
            if q["titleSlug"] not in used_lc
            and q["titleSlug"] not in existing_slugs
            and tags & {t["slug"] for t in q["topicTags"]}
        ]
        candidates.sort(key=lambda q: (diff_rank.get(q["difficulty"], 3), int(q["questionId"])))

        # Fallback for patterns whose tags yield too few matches.
        if len(candidates) < needed:
            for q in sorted(
                catalog,
                key=lambda q: (diff_rank.get(q["difficulty"], 3), int(q["questionId"])),
            ):
                if q["titleSlug"] in used_lc or q["titleSlug"] in existing_slugs:
                    continue
                if q not in candidates:
                    candidates.append(q)
                if len(candidates) >= needed:
                    break

        hint = pattern["short_description"].rstrip(".") + "."
        for q in candidates[:needed]:
            lc = q["titleSlug"]
            used_lc.add(lc)
            current.append(
                {
                    "order": len(current) + 1,
                    "name": q["title"],
                    "slug": lc,
                    "difficulty": q["difficulty"],
                    "leetcode_id": int(q["questionId"]),
                    "leetcode_slug": lc,
                    "leetcode_url": f"https://leetcode.com/problems/{lc}/",
                    "tags": [t["slug"] for t in q["topicTags"]],
                    "hint": hint,
                }
            )

    SEED.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Seed rebuilt: {len(patterns)} patterns, "
        f"{sum(len(p['problems']) for p in patterns)} problems"
    )


if __name__ == "__main__":
    main()
