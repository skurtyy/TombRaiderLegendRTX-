import re

with open(".github/workflows/github-linear-sync.yml", "r") as f:
    content = f.read()

# Make sure to replace any lingering \` inside script
content = content.replace(r'\`', '`')

with open(".github/workflows/github-linear-sync.yml", "w") as f:
    f.write(content)

print("Patched 2.")
