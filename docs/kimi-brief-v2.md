# Consulting brief: effbench UX/UI design pass v2

You are retained as the principal design consultant on this product. Channel the
finest data-visualization minds (McCandless' clarity, Tufte's ink-to-data
discipline, Ive's restraint, Benzi's drama) — in any galaxy, in any dimension —
and produce a consultant's report that will lead to "wow". You have full design
authority. We are not prescribing solutions; we are handing you the problem, the
evidence, and the constraints. You decide what the answer looks like.

---

## 1. The product

**effbench** — an open-source benchmark for local AI inference (any
OpenAI-compatible server: llama.cpp, LM Studio, Ollama, vLLM). One question
drives everything:

> **"How fast — and how accurate — is your local AI?"**

Its founding idea: speed alone is meaningless if the answers are wrong. So its
core metric is

    effective tok/s = raw tok/s × task pass-rate

A model that streams 200 tok/s of wrong answers scores lower than one that
streams 90 tok/s of right ones. 48 tasks across 6 purposes (code, reasoning,
extract, structure, summarise, chat), deterministic graders (no LLM-as-judge),
identical prompts forever (suites frozen for comparability).

Audience: a non-technical enthusiast who runs a local model on a gaming PC and
wants to know "is my setup good?" — plus a tweaker who changes quants, draft
models, context lengths and needs to see what each change did.

## 2. The surfaces (current, v0.6)

**A. Web UI** (localhost, single HTML file, no framework, no external assets):
brand masthead; run panel (Quick ~15s / Full 2–4min buttons, segmented
progress rail whose in-flight segment sweeps forever, pulse dot, current task
+ elapsed clock, task rows fading in as they resolve); a summary cluster after
a run (one big effective-t/s number, pass-rate arc); past-runs table with
compare; settings (server URL, runs, auto-open). Design language: void-black
background, graphite panel ramp, single mint accent, hairline rules, tabular
numerals, one motion scale. It should feel like a precision instrument, not a
dashboard.

**B. Report** (self-contained HTML, inline SVG, shareable/exportable):
hero cluster (56px effective t/s number, supporting metrics on a shared
micro-bar scale: wall median, gen-only median, mean, peak; pass-rate arc;
spec-decode accept strip); a purpose ladder (ranked horizontal rungs, pass
rate per purpose, n counts, zero-pass drawn as a visible sliver, untested
purposes listed under); per-task rows (pass/fail chip, task name, purpose tag,
tok/s, badges for "reference rig fails this too", fail hints); a band chart
(your wall median vs a "typical" band as a shaded region, gen-only marker,
p10–p90 strip, band source printed verbatim); compare view (two runs,
per-metric dumbbell rows with % deltas).

**C. Terminal** menu (fallback, text-only) — first-class but secondary.

## 3. The evidence and the live questions

### 3.1 The credibility of "typical"

A user ran our tool and read "typical 120–200 tok/s" against their measured
118 and worried their host was underperforming — while people on social media
report "200 t/s" on the same hardware. Investigation found:

- Social-media numbers are generation-only throughput (what llama.cpp prints
  per request), usually best-case: short outputs, warm cache, sometimes
  batched. This rig's generation-only p90 is 192, best 198 — it IS in that
  league. The gap was definitional.
- Our headline is deliberately wall-clock (includes prompt processing): cold
  runs read 66–118, warm-cache soaks read ~167. We label the band's source
  ("own warm-cache soak 2026-08-17, RTX 5090") — but it is still **n=1 rig:
  ours**.
- User's own words: *"It might be that others inflate their scores and we did
  also. How do we know what typical is?"*

**Question for you:** how should a small open-source tool present "typical"
with real credibility — without a server, without fake crowds? Consider tiers
of provenance (own history / community opt-in submissions / published claims),
and how each tier should be visually distinguished so n=1 never masquerades as
n=1000. Design the trust model visually.

### 3.2 Context: "other scores relative to mine"

User: *"It would be great to have context (other scores relative to the ones
just measured)."* After a run, the user wants to situate the number: vs their
own past runs, vs other hardware classes, vs other models/quants, vs the
claims they saw online. What's the minimal, credible, beautiful way to give
that context — and what must we refuse to show (invented data, unlabelled
aggregates)?

### 3.3 The value audit

User: *"another design pass, considering how to add more and how to ensure
that what is there is giving value."* Audit every current component (listed
in §2): does it earn its pixels? Which components answer the founding
question, which merely inform, which are decoration? Recommend additions (new
analyses, comparisons, explanations that deepen "how fast AND how accurate")
and — importantly — removals or mergers. A ruthless CUT list is as valuable
as an ADD list. The tool currently reports: effective t/s, wall median,
gen-only median, mean, peak, p10/p90, pass rate by purpose and per task,
expected-fail badges, fail hints, accept rate, hardware-fit band. Some of
this may be noise to our audience; tell us which.

### 3.4 Raw user feedback (verbatim, incl. the typos)

> "Here is bug on teh speed vs typical bit - it says 'band: mixed on this
> hardware — own warm-cache soak 2026-08-17, RTX 5090, b1-4df29benly
> (cache-invariant)' and it seems like it's two lines of text overlapping so I
> can't really make it out." *(now fixed: the two strings were overprinting;
> they're stacked now — but note how a provenance line dense enough to
> overprint is a design smell in itself)*

> "I am slightly concerned that despite all the model tuning, we still get low
> numbers compared to that of what others report and what we ourselves report
> […] I've seen many people talking about having 200t/s and while this may be
> peak, or best they achieved I would like to know our host is optimsed well."

> "I think that we care most about 'how fast — and how accurate — is your
> local AI?', so we should have a way of demonstrating that clearly."

> "It would be great to have context (other scores relative to the ones just
> measured)."

> "I would like another deisgn pass, considering how to add more and how to
> ensure that what is there is giving value."

## 4. Hard constraints (non-negotiable)

- Report = ONE self-contained HTML file: inline SVG/CSS, no external assets,
  no web fonts, no JS frameworks; must render from a file:// double-click and
  print cleanly.
- Web UI = one HTML file, vanilla JS only, served by a Python-stdlib localhost
  server; nothing leaves the machine (privacy is a product value).
- One design-token source (a Python module the report interpolates and the
  UI mirrors). Dark instrument aesthetic is the direction; challenge it only
  with something dramatically better, not fashionably different.
- Task suites, prompts and graders are frozen — design may add views, never
  change measurements.
- Every number must carry its provenance visibly. No invented reference data.
  If a suggestion needs data we don't have, say what to collect and how to
  label it honestly meanwhile.
- Accessible: reduced-motion respected, contrast, tabular numerals for all
  changing digits.
- Effective t/s stays the hero metric. The pass-rate × speed story is the
  product; do not bury it.

## 5. Deliverable

A consultant's report, structured as you see fit, that includes at minimum:

1. **Verdict** on the current design (§2) against the founding question —
   where it succeeds, where it evades.
2. **The value audit**: keep / merge / cut for every current component, with
   reasoning tied to the two audiences.
3. **The typicality & context design**: your full proposal for §3.1 + §3.2 —
   the trust/provenance model made visual; what "context after a run" looks
   like on first run vs fiftieth run.
4. **Additions**: ranked new components/analyses that deepen the speed×accuracy
   story (and any that need new data — flagged as such).
5. **Spec-level guidance** for the top 3 changes: layout, interaction, states
   (empty/busy/error/success), and how they behave on a phone-width screen.
6. **A cut list.**

Format: a single self-contained HTML report (same constraints as §4 apply to
your artifact), designed to your own standard — the report itself is a work
sample. Written for an engineer to implement without guessing: concrete
dimensions, hierarchy, copy suggestions, edge cases. Where you disagree with
anything in this brief, say so and argue it.
