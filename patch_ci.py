import re

with open(".github/workflows/ci.yml", "r") as f:
    content = f.read()

# Add set PYTHONPATH
content = content.replace("run: pytest tests_trl/ -v --tb=short --basetemp", 'env:\n          PYTHONPATH: .\n        run: pytest tests_trl/ -v --tb=short --basetemp')

with open(".github/workflows/ci.yml", "w") as f:
    f.write(content)

print("Patched CI.")
