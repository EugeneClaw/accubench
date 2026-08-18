#!/usr/bin/env python3
"""Adjudicate builder drafts: apply principal's verified corrections, output clean suites.

Principal review log (2026-08-17, verified against independent Python oracles):
- reasoning/arithmetic-remainder: builder answer 55 WRONG (123456789 % 997 = 273). Fixed.
- longform/acrostic-hex: impossible spec (6 lines must spell 7-letter HEXAGON).
  Fixed: 7 lines spelling HEXAGON.
- All other answers verified correct; fixtures present for all tasks.
"""
import json
import os
import re

DRAFTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "builder-drafts")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suites")

FIXES = {
    "arithmetic-remainder": {
        "grader": {"type": "regex", "pattern": r"ANSWER:\s*273\b"},
        "good_output": (
            "123456789 divided by 997:\n"
            "997 × 123828 = 123456516\n"
            "123456789 − 123456516 = 273\n"
            "ANSWER: 273"
        ),
        "bad_output": "997 × 123828 = 123456516, so the remainder is small.\nANSWER: 55",
    },
    "arithmetic-geometric-mean": {
        # original pattern ANSWER:\s*6 matched 'ANSWER: 6.5' by prefix — anchored
        "grader": {"type": "regex", "pattern": r"ANSWER:\s*6(?:\.0+)?\s*$"},
    },
    "prime-sieve": {
        # original 'bad' was actually correct code (slower sieve, same stdout)
        "bad_output": (
            "```python\nprimes = []\nfor i in range(3, 20):\n"
            "    is_prime = True\n"
            "    for j in range(2, i):\n"
            "        if i % j == 0:\n"
            "            is_prime = False\n"
            "            break\n"
            "    if is_prime:\n"
            "        primes.append(i)\n"
            "print(' '.join(map(str, primes)))\n```"
        ),
    },
    "acrostic-hex": {
        "prompt": (
            "Write a seven-line poem. The first letter of each line, when read "
            "vertically, must spell the word 'HEXAGON'. The lines must be numbered "
            "1 through 7, followed by a period and a space (e.g., '1. H...'). "
            "The rest of the content is your choice. Do not include any other text."
        ),
        "grader": {"type": "regex",
                   "pattern": r"^1\. H.*\n2\. E.*\n3\. X.*\n4\. A.*\n5\. G.*\n6\. O.*\n7\. N.*$"},
        "good_output": ("1. Hidden in plain sight,\n2. Every angle equal,\n"
                        "3. Xylophone-strange and even,\n4. A shape of bees,\n"
                        "5. Geometry's favorite child,\n6. One flat plane,\n"
                        "7. Never ending."),
        "bad_output": ("1. Hidden in plain sight,\n2. Every angle equal,\n"
                       "3. Six sides turning,\n4. A shape of bees,\n"
                       "5. Geometry's favorite child,\n6. One flat plane."),
    },
}

for name in ("reasoning", "code", "longform"):
    raw = open(os.path.join(DRAFTS, f"{name}.draft.json")).read()
    obj = json.loads(re.findall(r"\{[\s\S]*\}", raw)[-1])
    tasks = obj["tasks"]
    for t in tasks:
        if t["id"] in FIXES:
            t.update(FIXES[t["id"]])
            print(f"fixed {t['id']}")
    path = os.path.join(OUT, f"{name}.json")
    with open(path, "w") as f:
        json.dump({"tasks": tasks}, f, indent=2)
    print(f"{name}: {len(tasks)} tasks -> {path}")
