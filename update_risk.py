import re

with open(".github/workflows/_claude-pr-risk.yml", "r") as f:
    text = f.read()

text = text.replace("urllib.request.urlopen(req, timeout=10)", "urllib.request.urlopen(req)")
text = text.replace("with urllib.request.urlopen(req) as r:", "try:\n              with urllib.request.urlopen(req, timeout=15) as r:\n                  data = json.loads(r.read())\n          except urllib.error.HTTPError as e:\n              if e.code == 401:\n                  print('Risk: unknown (invalid auth)')\n                  exit(0)\n              raise")

with open(".github/workflows/_claude-pr-risk.yml", "w") as f:
    f.write(text)
