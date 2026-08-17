"""Deterministic graders. Pure: (grader_spec, content, reasoning) -> (bool, detail).

No LLM-as-judge. Same output twice = same verdict twice.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

MAX_CODE_LEN = 100_000  # refuse to exec absurd payloads
SAVED_STDOUT = sys.stdout  # keep a handle for safety in odd embeds


def _norm(text):
    """Normalise: strip trailing ws per line, exactly one trailing newline."""
    lines = [ln.rstrip() for ln in text.strip("\n").split("\n")]
    return "\n".join(ln for ln in lines).strip("\n")


def extract_code(content, language=None):
    """Return the last fenced code block (optionally language-tagged), else None."""
    pattern = r"```" + (language or r"\w*") + r"\s*\n(.*?)```"
    blocks = re.findall(pattern, content, re.DOTALL)
    return blocks[-1].strip("\n") if blocks else None


def grade(g, content, reasoning=""):
    """Dispatch on g['type']. Returns (passed: bool, detail: str)."""
    t = g.get("type")
    try:
        if t == "exact":
            return grade_exact(g, content)
        if t == "contains":
            return grade_contains(g, content)
        if t == "contains_all":
            return grade_contains_all(g, content)
        if t == "regex":
            return grade_regex(g, content)
        if t == "code":
            return grade_code(g, content)
        if t == "json":
            return grade_json(g, content)
        return False, f"unknown grader type: {t!r}"
    except Exception as e:
        return False, f"grader-error: {type(e).__name__}: {e}"


def grade_exact(g, content):
    want = g["expect"]
    got = _norm(content)
    if _norm(want) == got:
        return True, "exact match"
    return False, f"mismatch: got {len(got)} chars vs {len(_norm(want))} expected"


def grade_contains(g, content):
    needles = g.get("any_of") or [g["needle"]]
    for n in needles:
        if n in content:
            return True, f"found {n!r}"
    return False, f"none of {len(needles)} needles found"


def grade_contains_all(g, content):
    needles = g["needles"]
    missing = [n for n in needles if n not in content]
    if not missing:
        return True, f"all {len(needles)} present"
    return False, f"missing {missing[:3]}{'…' if len(missing) > 3 else ''}"


def grade_regex(g, content):
    rx = re.compile(g["pattern"], re.DOTALL | (0 if g.get("case_sensitive", True) else re.IGNORECASE))
    m = rx.search(content)
    if m:
        return True, f"matched at {m.start()}"
    return False, "no regex match"


def grade_code(g, content):
    lang = g.get("language", "python")
    if lang != "python":
        return False, f"unsupported language: {lang}"
    code = extract_code(content, "python") or extract_code(content)
    if not code:
        # whole reply is code? only if it looks like it
        if content.strip().startswith(("import ", "def ", "from ", "print(")):
            code = content.strip()
        else:
            return False, "no fenced code block found"
    if len(code) > MAX_CODE_LEN:
        return False, f"code too long ({len(code)} chars)"
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "sol.py")
        with open(path, "w") as f:
            f.write(code)
        try:
            r = subprocess.run(
                [sys.executable, path],
                input=g.get("stdin", ""),
                capture_output=True, text=True,
                timeout=g.get("timeout_s", 10), cwd=td)
        except subprocess.TimeoutExpired:
            return False, f"timeout after {g.get('timeout_s', 10)}s"
        if r.returncode != 0:
            return False, f"exit {r.returncode}: {r.stderr.strip()[:200]}"
        got = _norm(r.stdout)
        want = _norm(g["expect_stdout"])
        if got == want:
            return True, "stdout matched"
        g_lines, w_lines = got.split("\n"), want.split("\n")
        diff_at = next((i for i, (a, b) in enumerate(zip(g_lines, w_lines)) if a != b),
                       min(len(g_lines), len(w_lines)))
        return False, (f"stdout differs at line {diff_at + 1}: "
                       f"got {g_lines[diff_at][:60]!r} want {w_lines[diff_at][:60]!r}"
                       if diff_at < len(g_lines) and diff_at < len(w_lines)
                       else f"length mismatch: got {len(g_lines)} lines want {len(w_lines)}")


def grade_json(g, content):
    """Extract last JSON object/array from content and check keys/values."""
    m = re.findall(r"\{.*\}|\[.*\]", content, re.DOTALL)
    if not m:
        return False, "no JSON found"
    try:
        obj = json.loads(m[-1])
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}"
    for k, v in g.get("expect_keys", {}).items():
        if k not in obj:
            return False, f"missing key {k!r}"
        if v is not None and obj[k] != v:
            return False, f"key {k!r}: got {obj[k]!r} want {v!r}"
    return True, "json ok"
