"""Validate patterns_seed.json structure, links, and uniqueness."""

import json
import re
import sys
from collections import Counter
from pathlib import Path

SEED = Path(__file__).resolve().parents[1] / "app" / "seed" / "patterns_seed.json"
URL_RE = re.compile(r"^https://leetcode\.com/problems/[a-z0-9-]+/?$")
DIFFICULTIES = {"Easy", "Medium", "Hard"}
STAGES = {"Basic", "Intermediate", "Advanced"}


def main() -> int:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    patterns = data["patterns"]
    errors: list[str] = []
    all_lc: list[str] = []
    per_pattern: list[tuple[str, int]] = []
    diffs: Counter = Counter()
    stages: Counter = Counter()

    pattern_slugs = set()
    for pattern in patterns:
        slug = pattern["slug"]
        if slug in pattern_slugs:
            errors.append(f"Duplicate pattern slug: {slug}")
        pattern_slugs.add(slug)

        if pattern.get("stage") not in STAGES:
            errors.append(f"{slug}: invalid stage {pattern.get('stage')!r}")
        stages[pattern.get("stage")] += 1

        seen_local = set()
        orders = []
        for problem in pattern.get("problems", []):
            label = f"{slug}/{problem.get('slug')}"
            orders.append(problem.get("order"))
            diffs[problem.get("difficulty")] += 1

            if problem.get("difficulty") not in DIFFICULTIES:
                errors.append(f"{label}: invalid difficulty")
            url = problem.get("leetcode_url", "")
            if not URL_RE.match(url):
                errors.append(f"{label}: invalid LeetCode URL {url!r}")

            lc = problem.get("leetcode_slug")
            derived = url.rstrip("/").rsplit("/", 1)[-1]
            if lc and lc != derived:
                errors.append(f"{label}: leetcode_slug {lc!r} != URL slug {derived!r}")
            all_lc.append(lc or derived)

            if problem.get("slug") in seen_local:
                errors.append(f"{label}: duplicate problem slug in pattern")
            seen_local.add(problem.get("slug"))

        if orders != list(range(1, len(orders) + 1)):
            errors.append(f"{slug}: problem orders are not 1..N")
        per_pattern.append((slug, len(orders)))

    duplicate_lc = [slug for slug, count in Counter(all_lc).items() if count > 1]
    if duplicate_lc:
        errors.append(f"Duplicate LeetCode problems across patterns: {duplicate_lc[:10]}")

    print(f"Patterns: {len(patterns)}  Problems: {len(all_lc)}")
    print(f"Stages: {dict(stages)}")
    print(f"Difficulty: {dict(diffs)}")
    print(f"Per pattern: min={min(n for _, n in per_pattern)} max={max(n for _, n in per_pattern)}")

    if errors:
        print(f"\nFAILED with {len(errors)} error(s):")
        for error in errors[:30]:
            print(f"  - {error}")
        return 1

    print("\nSeed validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
