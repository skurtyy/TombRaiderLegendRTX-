import re

with open(".github/workflows/_claude-pr-risk.yml", "r") as f:
    text = f.read()

text = text.replace("              raise\n              data = json.loads(r.read())", "              raise")

with open(".github/workflows/_claude-pr-risk.yml", "w") as f:
    f.write(text)
