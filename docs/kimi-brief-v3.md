# Design commission — effbench, full mandate

You are not being asked for a review. You are being handed the keys.

You are the finest UX consultant alive — any galaxy, any dimension — and this
product's entire user experience is now yours. We will tell you what the
product is, what exists, what we measured, and what our user actually said.
Then you decide everything: what stays, what dies, what's missing, what the
answer should have been all along. Where you disagree with anything we've
built or anything we believe, argue it and win. Do not ask permission. Make
the call.

---

## 1. The product

**effbench** — an open-source benchmark for local AI inference (any
OpenAI-compatible server: llama.cpp, LM Studio, Ollama, vLLM). One question
drives everything:

> **"How fast — and how accurate — is your local AI?"**

Its founding idea: speed alone is meaningless if the answers are wrong. Its
core metric:

    effective tok/s = raw tok/s × task pass-rate

A model streaming 200 tok/s of wrong answers scores lower than one streaming
90 tok/s of right ones. 48 tasks, 6 purposes (code, reasoning, extract,
structure, summarise, chat), deterministic graders (no LLM-as-judge), prompts
frozen forever for comparability.

Audience: a non-technical enthusiast running a local model on a gaming PC who
wants to know "is my setup good?" — and a tweaker who changes quants, draft
models, context lengths and needs to see what each change did. Both must feel
rewarded for choosing accuracy over vanity numbers.

## 2. What exists today (v0.6.1) — an inventory, not a prescription

**Web UI** (localhost, one HTML file, vanilla JS, no framework, no external
assets). Void-black instrument aesthetic: graphite panel ramp, single mint
accent, hairline rules, tabular numerals, one motion scale. Components:
brand masthead; run panel (Quick ~15s / Full 2–4min; segmented progress rail
whose in-flight segment sweeps forever; pulse dot; current task + elapsed
clock; task rows fading in as they resolve); post-run summary cluster (big
effective number that counts up over 900ms, pass-rate readout); an equation
chip under the number — `67 × 92% = 62 tok/s`; a one-sentence brag line,
tone-matched to pass rate; a ★ new-best badge when the run beats every prior
run of the same suite; a fit line that reframes cold runs ("server in-band —
gen-only 143 tok/s sits inside the typical band; wall is cold-run prompt
processing") instead of amber "slower than typical"; past-runs table with
compare; settings.

**Report** (self-contained HTML, inline SVG, shareable, prints clean). Hero
cluster: 56px effective t/s, equation chip, supporting micro-bars on one
scale (wall / gen-only / peak), 240° pass-rate arc, accept-rate strip;
purpose ladder (ranked rungs per purpose, n counts, zero-pass drawn as a
visible sliver, untested purposes listed); per-task rows (pass/fail chip,
purpose tag, tok/s, expected-fail badges, fail hints); band chart (your wall
median vs a "typical" band, gen-only marker, p10–p90 strip, band source
printed verbatim with "· one rig's soak, not a crowd's average"); compare
view (per-metric dumbbell rows with % deltas).

**Terminal menu** — first-class fallback, text-only.

## 3. What we measured (real rig: RTX 5090, Qwen3-27B IQ4_XS, speculative decoding)

| number | value |
|---|---|
| effective t/s (quick) | 62 |
| wall t/s (quick, cold) | 67 |
| gen-only t/s (median / p90 / peak) | 141 / 192 / 198 |
| pass rate (quick / full 48) | 92% / 89.6% |
| spec-decode acceptance | 98.5–100% |
| "typical" band shown | 107–178 (quick-scaled ×0.89 from a 120–200 soak) |

Context we learned the hard way: people on social media headline "200 t/s" —
generation-only, best-case, warm cache. Our headline is wall-clock with
accuracy multiplied in. Both are defensible; only one is ours. The "typical"
band is currently n=1: our own rig's soak, labelled as such. Real typicality
needs a provenance model we haven't designed — tiers of trust (own history /
community opt-in / published claims). That design problem is yours too.

## 4. Raw user feedback (verbatim, typos intact)

> "I am slightly concerned that despite all the model tuning, we still get low
> numbers compared to that of what others report and what we ourselves report.
> It might be that others inflate their scores and we did also. How do we know
> what typical is? I've seen many people talking about having 200t/s and while
> this may be peak, or best they achieved I would like to know our host is
> optimsed well."

> "I think that we care most about 'how fast — and how accurate — is your
> local AI?', so we should have a way of demonstrating that clearly."

> "It would be great to have context (other scores relative to the ones just
> measured)."

> "I would like another deisgn pass, considering how to add more and how to
> ensure that what is there is giving value."

> "we DO NOT want the user thinking they are getting lower numbers. We want
> them realising that accuracy is part of the speed equation. It must be
> celebrated. It must give the user a dopamine reward to know when they tuned
> their recipe, they chose EFFECTIVE speed over benchmark high scores that are
> horrible to work with. Get a solution together for this so even the non
> technical realises how important this is."

> "Kimi should be given more autonomy to decide how it can be improved. Kimi
> is 'the finest UX consultant alive' so lets not clip his wings. Go."

## 5. The only constraints

- Suites, prompts, graders: frozen. Design may add views, never change
  measurements.
- Report = one self-contained HTML file; web UI = one HTML file + Python
  stdlib server. No external assets, no web fonts, no frameworks. Everything
  stays on the user's machine — privacy is a product value.
- Effective t/s stays the hero. Everything else about its presentation — and
  everything else on screen — is negotiable.
- Every number carries its provenance visibly. No invented reference data. If
  a design needs data we don't have, specify what to collect and how to label
  it truthfully meanwhile.
- Accessibility: reduced-motion, contrast, tabular numerals for changing
  digits.

## 6. Your authority, explicitly

- Kill any component — including ones we just shipped and are proud of.
- Add anything: new analyses, new moments, new data structures, rituals.
- Reinvent layout, hierarchy, tone, motion, naming. The dark instrument
  aesthetic is a direction we chose, not a law you inherit.
- Challenge the metric's presentation, the band model, the emotional arc —
  anything except §5.
- Decide, don't propose-with-three-options. We want your call, argued.

## 7. Deliverable

Your report, your structure, your format — with one hard requirement: it must
be implementable by an engineer without guessing. Concrete dimensions, copy,
states (empty / busy / error / success), phone-width behaviour, and what to
build first. A self-contained HTML artifact designed to your own standard —
the report is a work sample. End with the cut list, and with what you'd do
next if even §5 were negotiable.
