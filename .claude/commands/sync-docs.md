---
description: Sync WHITEBOARD.md, CHANGELOG.md, README.md, CLAUDE.md against latest build evidence. Demotes unverified "Believed Resolved" claims. Run at session end.
allowed-tools: Task, Read, Write, Edit
---

Delegate to the `doc-sync` subagent.

After completion, show the sync report and ask whether to commit:
```
git add CLAUDE.md WHITEBOARD.md CHANGELOG.md README.md
git commit -m "doc-sync: <report summary>"
```

Do NOT auto-push.
