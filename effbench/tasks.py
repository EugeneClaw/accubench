"""Load and validate task suites (JSON files or a directory of them)."""
import json
import os

REQUIRED = ("id", "prompt", "grader")
GRADER_TYPES = {"exact", "contains", "contains_all", "regex", "code", "json"}


def load_suite(path):
    """Load tasks from a JSON file or a directory of *.json files. Returns list, sorted by id."""
    files = []
    if os.path.isdir(path):
        files = sorted(os.path.join(path, f) for f in os.listdir(path) if f.endswith(".json"))
    elif os.path.isfile(path):
        files = [path]
    else:
        raise FileNotFoundError(f"suite not found: {path}")
    tasks = []
    for fp in files:
        with open(fp) as f:
            data = json.load(f)
        items = data["tasks"] if isinstance(data, dict) else data
        for t in items:
            problems = validate_task(t)
            if problems:
                raise ValueError(f"{fp}: task {t.get('id', '?')!r}: {'; '.join(problems)}")
            tasks.append(t)
    ids = [t["id"] for t in tasks]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate task ids: {sorted(dupes)}")
    return sorted(tasks, key=lambda t: t["id"])


def validate_task(t):
    problems = []
    if not isinstance(t, dict):
        return ["task is not an object"]
    for k in REQUIRED:
        if k not in t:
            problems.append(f"missing {k!r}")
    g = t.get("grader")
    if isinstance(g, dict):
        if g.get("type") not in GRADER_TYPES:
            problems.append(f"bad grader type {g.get('type')!r}")
        if g.get("type") == "code" and "expect_stdout" not in g:
            problems.append("code grader needs expect_stdout")
        if g.get("type") in ("exact", "contains") and not (
                "expect" in g or "needle" in g or "any_of" in g):
            problems.append("grader needs expect/needle/any_of")
    elif g is not None:
        problems.append("grader must be an object")
    return problems
