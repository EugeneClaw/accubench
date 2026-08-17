"""Hardware-typical raw t/s expectations.

Provides 'what's fast for your hardware' context in the report.
Numbers are conservative medians from public benchmarks and community reports.
The point is not precision — it's giving the user a sense of 'typical'.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "expectations.json")


def _load():
    with open(DATA_PATH) as f:
        return json.load(f)


def detect_hw_class(props, observed_raw_tps=None):
    """Best-effort detect hardware class from server /props.

    llama.cpp /props is inconsistent across builds. We use whatever signal
    is exposed (build_info, slot count, etc.) and fall back to inferring
    from observed raw t/s when signals are missing.

    Returns one of: phone_laptop, desktop_gpu_mid, desktop_gpu_high,
                    workstation, dataclass.

    Note: thresholds here are calibrated against the FULL effbench suite
    (36 tasks, ~167 t/s for RTX 5090 + Qwen3.8-27B IQ4_XS). Quick suite
    medians are systematically lower (~70 t/s on the same machine) because
    reasoning tasks drag the median down. If you only ran the quick suite,
    trust the *class* but not the precise number.
    """
    try:
        info = props.get("build_info", {}) or {}
        if isinstance(info, str):
            build_str = info
        else:
            build_str = " ".join(f"{k}={v}" for k, v in info.items())
        total_slots = props.get("total_slots", 0) or 0
    except Exception:
        total_slots = 0
        build_str = ""
    lower = str(build_str).lower()

    # Explicit GPU signals (preferred)
    if "cuda" in lower or "metal" in lower or "vulkan" in lower or "hip" in lower:
        # Mac Metal + 1 slot = integrated; could still be M-series Ultra though
        if "metal" in lower and total_slots <= 1:
            return "desktop_gpu_mid"
        return "desktop_gpu_high"
    # Multiple slots often = server/workstation setup
    if total_slots >= 4:
        return "workstation"

    # No GPU signal: infer from observed t/s if given.
    # Thresholds here assume the FULL 36-task suite (median).
    if observed_raw_tps is not None:
        if observed_raw_tps > 200:
            return "dataclass"
        if observed_raw_tps > 100:
            return "desktop_gpu_high"
        if observed_raw_tps > 30:
            return "desktop_gpu_mid"
        return "phone_laptop"

    return "phone_laptop"


def detect_model_arch(model_path):
    """Extract a coarse model arch token from the model path/filename.

    Filename conventions vary wildly:
      qwen3-27B           → qwen3.27_b
      Qwen3.8-27B         → qwen3.27_b  (8 is minor version)
      qwen3_8b            → qwen3.8_b
      Qwen3-4B-Instruct   → qwen3.4_b
      llama-3-8b          → llama3_8b

    Rule: find ALL sizes anywhere in the filename; the LARGEST size is
    the parameter count. qwen3.8-27B → both 8 and 27 match, pick 27."""
    if not model_path:
        return ""
    name = os.path.basename(model_path).lower()
    # Sizes to look for, with optional trailing 'b'
    sizes = ("0.6", "1.7", "4", "8", "14", "27", "32", "70", "72")
    if "qwen3" in name:
        matches = []
        for size in sizes:
            for sep in ("-", "_", "."):
                for suffix in ("", "b"):
                    token = f"{sep}{size}{suffix}"
                    # token must appear, but NOT inside the 'qwen3.X' minor-version spot
                    idx = name.find(token)
                    if idx > 0:
                        # reject if immediately preceded by a digit+dot (e.g., '3.8' has '.8' preceded by '3')
                        prev = name[idx - 1]
                        if prev.isdigit() and sep == ".":
                            # likely the minor version (qwen3.8)
                            # only reject when there's no other size hint later
                            # simpler: if 'qwen3.X' exists in name, ignore that X for the major
                            continue
                        matches.append(size)
        if matches:
            best = max(matches, key=lambda s: float(s))
            return f"qwen3.{best}_b"
        return "qwen3_unknown_b"
    if "llama-3" in name or "llama3" in name:
        for size in ("8b", "70b"):
            if size in name:
                return f"llama3_{size}"
    return ""


def detect_quant(model_path):
    """Extract quant token from filename (e.g., IQ4_XS, Q5_K_M)."""
    if not model_path:
        return ""
    base = os.path.basename(model_path).upper()
    for q in ("IQ4_XS", "IQ4_XXS", "Q4_K_M", "Q4_K_S", "Q5_K_M", "Q5_K_S",
              "Q8_0", "F16", "BF16"):
        if q in base:
            return q.replace("IQ4", "iq4")  # normalise case
    return ""


def lookup(hw_class, model_arch, quant):
    """Return the (lo, hi) typical raw t/s band, or None if no data."""
    data = _load()
    for e in data["entries"]:
        if (e["hw_class"] == hw_class and
            e["model_arch"] == model_arch and
            e["quant"] == quant):
            return (e["tok_s_lo"], e["tok_s_hi"], e.get("ref_url", ""))
    # try relaxing quant
    for e in data["entries"]:
        if e["hw_class"] == hw_class and e["model_arch"] == model_arch:
            return (e["tok_s_lo"], e["tok_s_hi"], e.get("ref_url", ""))
    # relax model too
    for e in data["entries"]:
        if e["hw_class"] == hw_class:
            return (e["tok_s_lo"], e["tok_s_hi"], e.get("ref_url", ""))
    return None


def classify_fit(observed_tps, band):
    """Where does observed_tps sit in the band? 'above' / 'in' / 'below'."""
    if band is None:
        return "unknown"
    lo, hi, _ = band
    if observed_tps > hi * 1.10:
        return "above"   # noticeably better than typical
    if observed_tps < lo * 0.85:
        return "below"
    return "in"


def hw_class_blurb(hw_class):
    """Plain-English description of a hardware class."""
    data = _load()
    return data.get("_hw_class_blurbs", {}).get(hw_class, "")