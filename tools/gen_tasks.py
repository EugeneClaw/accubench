#!/usr/bin/env python3
"""Dispatch task-bank drafting to the local MAIN door. Output to builder-drafts/."""
import json
import os
import re
import urllib.request

URL = os.environ.get("ACCUBENCH_URL", "http://localhost:11434") + "/v1/chat/completions"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "builder-drafts")
os.makedirs(OUT, exist_ok=True)

COMMON = """You are drafting tasks for a deterministic benchmark suite that measures
local LLM servers. Tasks must be solvable by pure reasoning — no trivia recall,
no cultural knowledge, nothing ambiguous. Every task has exactly one verifiable
correct outcome. A grader script will judge outputs mechanically, so the expected
answers must be exact.

Return STRICT JSON only — no prose before or after. Shape:

{"tasks": [
  {"id": "kebab-case-unique-id",
   "category": "<category>",
   "prompt": "<the user-facing instruction>",
   "max_tokens": <256-1024>,
   "temperature": 0.0,
   "grader": {"type": "<grader>", ...grader fields...},
   "good_output": "<an output that MUST pass the grader>",
   "bad_output": "<an output that MUST fail the grader>"
  }
]}

Grader types available:
- {"type":"exact","expect":"<full expected normalised text>"}
- {"type":"contains","needle":"<substring>"} or {"type":"contains","any_of":["a","b"]}
- {"type":"contains_all","needles":["a","b","c"]}
- {"type":"regex","pattern":"<python re>"}
- {"type":"code","language":"python","expect_stdout":"<exact stdout>","stdin":"","timeout_s":10}
  (code tasks: prompt asks for a fenced python block; grader execs the LAST
   ```python block and compares normalised stdout: per-line rstrip, join by \\n)
- {"type":"json","expect_keys":{"key":<value or null to only check presence>}}

Rules:
- good_output/bad_output are fixtures to self-test the grader: good MUST pass,
  bad MUST fail. Make them realistic (a believable near-miss, not "garbage").
- For code tasks, good_output must contain a correct fenced python solution
  whose stdout equals expect_stdout EXACTLY. bad_output: plausible but wrong.
- No task may depend on the current date, news, or model identity.
- Diverse difficulty: some trivial, some genuinely hard."""

SUITES = {
    "reasoning": COMMON + """

Suite: reasoning (category "reasoning", 10 tasks). Graders: mostly exact/contains.
Ideas: multi-step arithmetic word problems, sequence continuation, logic puzzles
with unique solutions, unit conversions, combinatorics with small counts, date
arithmetic on fixed dates, probability with clean fractions/decimals.
Ask the solver to end with "ANSWER: <value>" and grade with a regex capturing it
where exact-full-text grading is too brittle.""",
    "code": COMMON + """

Suite: code (category "code", 10 tasks). All graders type "code".
Ideas: fizzbuzz variants, string reversal/normalisation, frequency counts with
sorted deterministic output, small class/datatstructure ops printing state,
matrix operations, checksum/digit-sum, parsing compact input into ordered output,
simulation of simple rules (cellular/game-of-life few steps, tiny grid).
Keep runtimes < 1s and stdout <= 30 lines. Every program must print SOMETHING
(never rely on return values).""",
    "longform": COMMON + """

Suite: longform (category "longform", 8 tasks). Graders: contains_all / regex / json.
Ideas: write exactly N items each on its own numbered line; produce a JSON object
with given keys and specific computed values; write text where each paragraph
must begin with a given word; emit a markdown table with exact header cells;
produce exactly N bullet lines matching a pattern; acrostic-style constraints.
Structural constraints only — never grade writing quality.""",
}


def call(name, sys_prompt):
    body = json.dumps({
        "model": "builder",
        "messages": [{"role": "user", "content": sys_prompt}],
        "max_tokens": 9000,
        "temperature": 0.7,
        # burnout fix: uncapped CoT eats the whole budget before content.
        # disable thinking; if server ignores it, fall back to reasoning_content.
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        data = json.loads(r.read())
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    if not content.strip():
        # thinking-only response: mine the reasoning instead
        content = (msg.get("reasoning_content") or "")
        # strip think tags if present
        content = re.sub(r"</?think>", "", content)
        print(f"{name}: content empty, recovered {len(content)} chars from reasoning", flush=True)
    path = os.path.join(OUT, f"{name}.draft.json")
    open(path, "w").write(content)
    # quick shape check
    m = re.findall(r"\{.*\}", content, re.DOTALL)
    n = "NO-JSON" if not m else "?"
    if m:
        try:
            obj = json.loads(m[-1])
            n = f"{len(obj.get('tasks', []))} tasks"
        except json.JSONDecodeError as e:
            n = f"INVALID-JSON: {e}"
    print(f"{name}: {len(content)} chars -> {path}  [{n}]", flush=True)


for name, prompt in SUITES.items():
    try:
        call(name, prompt)
    except Exception as e:
        print(f"{name}: FAILED {e}", flush=True)
print("done", flush=True)
