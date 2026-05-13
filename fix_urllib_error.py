with open(".github/workflows/_claude-pr-risk.yml", "r") as f:
    content = f.read()

old_code = """          with urllib.request.urlopen(req) as r:
              data = json.loads(r.read())"""

new_code = """          try:
              with urllib.request.urlopen(req) as r:
                  data = json.loads(r.read())
          except urllib.error.HTTPError as e:
              print("HTTP Error:", e.code)
              print("Response:", e.read().decode('utf-8'))
              raise"""

content = content.replace(old_code, new_code)

with open(".github/workflows/_claude-pr-risk.yml", "w") as f:
    f.write(content)
