"""Design tokens — the single source of truth for both surfaces.

Instrument aesthetic: void-black panel, four-step graphite ramp, one mint
accent. Reports interpolate these into their CSS; the web UI loads the same
values through /api/tokens. Surfaces can never drift apart again.
"""

# Surface ramp: page -> panels -> raised/hover -> the only border color
VOID = "#07090D"
CARBON = "#0D1117"
GRAPHITE = "#161C24"
HAIRLINE = "#1F2733"

# Ink ramp
INK = "#E8EDF4"      # primary text / numerals
INK2 = "#9AA6B5"     # secondary text
INK3 = "#5C6875"     # labels / tertiary / tracks
INK_TRACK = "#10151C"  # chart tracks sit darker than graphite

# The accent — instrument light. One glow per screen, on the hero number.
MINT = "#4FE3C1"

# Verdict colors — semantics only, never chrome
PASS = "#4ADE80"
WARN = "#FBBF24"
FAIL = "#F87171"

# Type stacks (OS-native, zero loading)
SANS = "-apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"

# Motion scale (ms) — 140 for hovers, 240 for panels, 160 for row arrivals
D_HOVER = 140
D_PANEL = 240
D_ROW = 160

# CSS custom properties, shared by both surfaces
def css_vars():
    return f"""
    --void: {VOID}; --carbon: {CARBON}; --graphite: {GRAPHITE};
    --hairline: {HAIRLINE}; --ink: {INK}; --ink2: {INK2}; --ink3: {INK3};
    --ink-track: {INK_TRACK}; --mint: {MINT};
    --pass: {PASS}; --warn: {WARN}; --fail: {FAIL};
    """
