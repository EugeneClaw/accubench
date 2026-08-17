# Pull request

## What this changes

<!-- 1-3 sentences. -->

## Why

<!-- What problem does this solve? What's the use case? -->

## How you tested it

<!-- selftest, manual runs, etc. -->

## Checklist

- [ ] `python3 -m effbench validate --suite suites/quick.json` passes
- [ ] `python3 tools/selftest.py` passes
- [ ] If you added a task, both good_output and bad_output validate
- [ ] If you changed defaults or templates, regenerated example reports are still clean
- [ ] No real LAN IPs, no personal info, no secrets in any file