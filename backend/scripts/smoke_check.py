import sys
import urllib.request

PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"
BASE = f"http://127.0.0.1:{PORT}"
CHECKS = {
    "/dashboard": "Stage progress",
    "/patterns": "stage-advanced",
    "/patterns/two-pointers": "Copy template",
    "/problems": "data-table",
    "/review": "Review Queue",
}

for path, needle in CHECKS.items():
    body = urllib.request.urlopen(BASE + path, timeout=20).read().decode()
    print(path, "OK" if needle in body else "MISSING")
