---
description: Run the overnight 40-build test loop. Disables Windows sleep, executes run.py for up to 40 iterations, consults reviewers after each FAIL, then restores power settings.
allowed-tools: Task, Bash, Read, Write
---

Pre-flight checks (FAIL FAST if any fail):
1. Verify `GhidraMCP` is up on `localhost:8080` (curl test)
2. Verify game install path exists
3. Verify git working tree is clean (no uncommitted changes)
4. Verify `proxy.ini` is present

Then disable Windows sleep:
```powershell
powercfg /requestsoverride PROCESS trl.exe SYSTEM
powercfg /change standby-timeout-ac 0
```

Spawn `build-test-runner` subagent with "overnight" mode. After each FAIL build, consult:
- `terrain-drawable-investigator` for the next address to investigate
- `culling-patch-reviewer` for risk assessment of the proposed patch
- `hash-stability-auditor` if hash instability is suspected

Stop conditions:
- 40 builds completed
- Hard blocker requiring human input (document in CHANGELOG.md and stop)
- PASS on all 5 criteria

On completion or stop, restore power settings:
```powershell
powercfg /change standby-timeout-ac 30
```

Final summary: total builds, pass/fail counts, top blockers identified, recommended next-session focus.
