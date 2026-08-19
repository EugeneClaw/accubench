"""Translate task IDs and grader types into plain-English purpose/difficulty.

Non-technical users never need to read grader details. They want to know:
'Was it good for chat? For writing code? For pulling structured info?'
"""

# Purpose tags — what real-world use a task is a proxy for.
PURPOSES = ("chat", "code", "reasoning", "extract", "structure", "summarise")

# Difficulty bands — calibrated against the Qwen3.8-27B IQ4_XS typical pass.
DIFFICULTIES = ("easy", "medium", "hard")

# Hand-curated overrides: each task ID maps to (purpose, difficulty, plain_title).
# Tasks without an entry here fall back to heuristics from the grader type.
TASK_PROFILES = {
    # quick.json
    "q-fizzbang":          ("code",       "medium", "Write code with a tricky rule (fizzbuzz variant)"),
    "q-reverse":           ("code",       "easy",   "One-line string manipulation"),
    "q-palindrome":        ("code",       "easy",   "Yes/no classification"),
    "q-sum-sq":            ("code",       "easy",   "Simple loop and a print"),
    "q-fib10":             ("reasoning",  "easy",   "A sequence completion"),
    "q-chat-greeting":     ("chat",       "easy",   "Reply like a person, not a manual"),
    "q-wordcount":         ("extract", "medium", "Count words in a sentence"),
    "q-handshakes":        ("reasoning",  "medium", "Count combinations"),
    "q-prob-coin":         ("reasoning",  "medium", "Probability from first principles"),
    "q-prime-sieve":       ("code",       "medium", "Primality testing in a loop"),
    "q-json-config":       ("structure",  "easy",   "Build a JSON object with specific keys"),
    "q-markdown-table":    ("structure",  "medium", "Produce a markdown table"),
    "q-bullets":           ("structure",  "easy",   "Format a list on demand"),

    # seed.json
    "word-count-sentence": ("extract", "medium", "Count words in a sentence"),
    "arith-chain-discount":("reasoning",  "hard",   "Multi-step percentage math"),
    "logic-three-boxes":   ("reasoning",  "hard",   "Deductive logic puzzle"),
    "seq-triangle-numbers":("reasoning",  "easy",   "Recognise the sequence and continue"),
    "code-fizzbang":       ("code",       "medium", "Write code with a tricky rule (fizzbuzz variant)"),
    "code-word-freq":      ("code",       "medium", "Tally items in a collection"),
    "longform-five-rules": ("summarise", "medium", "Write a list following rules"),
    "json-config-build":   ("structure",  "easy",   "Build a JSON object with specific keys"),

    # reasoning.json
    "arithmetic-remainder":       ("reasoning", "hard",   "Big-number division"),
    "sequence-fibonacci-10th":    ("reasoning", "easy",   "A sequence completion"),
    "logic-soduko-unique":        ("reasoning", "hard",   "Deductive grid puzzle"),
    "unit-conversion-miles-to-km":("reasoning", "easy",   "Unit conversion"),
    "combinatorics-handshakes":   ("reasoning", "medium", "Count combinations"),
    "date-arithmetic-days":       ("reasoning", "medium", "Date math"),
    "probability-coin-toss":      ("reasoning", "medium", "Probability from first principles"),
    "logic-knights-knaves":       ("reasoning", "hard",   "Truth-teller / liar puzzle"),
    "arithmetic-geometric-mean":  ("reasoning", "easy",   "Geometric mean"),
    "logic-light-switches":       ("reasoning", "hard",   "Multi-step state reasoning"),

    # code.json
    "sum-of-squares":     ("code", "easy",   "Simple loop and a print"),
    "reverse-string":     ("code", "easy",   "One-line string manipulation"),
    "char-frequency":     ("code", "medium", "Tally items in a collection"),
    "matrix-transpose":   ("code", "medium", "Indexed access, formatted output"),
    "gcd-lcm":            ("code", "medium", "Library use + a print loop"),
    "palindrome-check":   ("code", "easy",   "Yes/no classification"),
    "prime-sieve":        ("code", "medium", "Primality testing in a loop"),
    "digit-sum":          ("code", "easy",   "Digit iteration"),
    "fibonacci-seq":      ("code", "easy",   "Loop building a list"),
    "grid-symmetry":      ("code", "medium", "Indexed comparison across axes"),

    # longform.json
    "five-odd-squares":       ("structure", "medium", "Numbered list with a strict format"),
    "json-factorial-sum":     ("structure", "medium", "Compute then emit clean JSON"),
    "paragraph-starts-with":  ("structure", "hard",   "Multiple paragraphs with anchor words"),
    "markdown-table-primes":  ("structure", "medium", "Produce a markdown table"),
    "bullet-multiples-of-3":  ("structure", "easy",   "Format a list on demand"),
    "acrostic-hex":           ("structure", "hard",   "First letter of each line spells a word"),
    "json-gcd-lcm":           ("structure", "medium", "Compute then emit clean JSON"),
    "numbered-even-cubes":    ("structure", "medium", "Numbered list with a strict format"),
}


def for_task(task_id):
    """Return (purpose, difficulty, plain_title) or heuristic fallback."""
    if task_id in TASK_PROFILES:
        return TASK_PROFILES[task_id]
    # heuristic fallback: infer purpose from grader type
    gtype = (task_id or "").lower()
    if "code" in task_id:
        return ("code", "medium", "Write code")
    if "json" in task_id:
        return ("structure", "medium", "Produce structured JSON")
    return ("reasoning", "medium", "General reasoning")


# Purpose copy for the human-facing report. Keep these SHORT and warm.
PURPOSE_DESCRIPTIONS = {
    "chat":       "Conversational answers, explanations, anything a person reads.",
    "code":       "Writing or fixing code. We actually run it.",
    "reasoning":  "Math, logic, planning, multi-step problems.",
    "extract":    "Pulling specific info out of text.",
    "structure":  "Producing structured output — JSON, tables, specific formats.",
    "summarise":  "Condensing text or making lists.",
}

# Difficulty copy.
DIFFICULTY_DESCRIPTIONS = {
    "easy":   "Trivial — most models get these.",
    "medium": "Needs attention; common weak spot for small models.",
    "hard":   "Pushes the model. Where strengths and weaknesses show.",
}

# What a fail means + what to try, keyed by (purpose, difficulty).
# Tone: factual, non-alarming, actionable. A fail is data, not a disaster.
FAIL_HINTS = {
    ("reasoning", "hard"): (
        "Hard multi-step reasoning — the common weak spot at this model size. "
        "Try: --think (let it reason), a higher quant, or a bigger model. "
        "Recipe tweaks (spec decode, context) rarely fix a reasoning fail."
    ),
    ("reasoning", "medium"): (
        "Mid-tier reasoning slip. Try --think first; if it persists, this is "
        "approaching the model's ceiling."
    ),
    ("reasoning", "easy"): (
        "Easy reasoning failed — unusual. Check the answer: if it's correct "
        "but differently phrased, it's a formatting miss, not a reasoning one."
    ),
    ("structure", "hard"): (
        "Strict formatting under load — the hardest thing to ask of a model. "
        "Bigger/higher-quant models do better; recipes rarely move this."
    ),
    ("structure", "medium"): (
        "Formatting slip. Often the model computed the right answer but "
        "wrapped it wrong. A higher quant or a stronger model helps; so does "
        "a stricter system prompt in your app."
    ),
    ("structure", "easy"): (
        "Simple formatting failed — surprising. Read the model's answer; if "
        "the content is right, it's presentation, not capability."
    ),
    ("code", "hard"): (
        "Code failed on a harder task. Check whether the code ran at all vs "
        "produced wrong output — the first is formatting, the second is real."
    ),
    ("code", "medium"): (
        "Code slip. Commonly an off-by-one or edge case. Higher quant or "
        "bigger model helps; spec-decode settings rarely change code accuracy."
    ),
    ("code", "easy"): (
        "Easy code task failed — unusual. Look at the raw answer: often the "
        "model added prose the grader (rightly) rejected."
    ),
}

# Fallback when (purpose, difficulty) isn't in FAIL_HINTS.
FAIL_HINT_DEFAULT = (
    "Check the model's answer against what the grader wanted. If the content "
    "is right but the shape is wrong, it's a formatting miss; otherwise it's "
    "a capability limit — try --think, a higher quant, or a bigger model."
)


def fail_hint(purpose, difficulty):
    """Plain-English: what this fail means and what to try."""
    return FAIL_HINTS.get((purpose, difficulty), FAIL_HINT_DEFAULT)