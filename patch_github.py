import re

with open(".github/workflows/github-linear-sync.yml", "r") as f:
    content = f.read()

# Fix the template literal escaping
# Replace makeLinearRequest(\` with makeLinearRequest(` and \`) with `)
content = content.replace(r'makeLinearRequest(\`', r'makeLinearRequest(`')
content = content.replace(r'\`)', r'`)')
content = content.replace(r'console.log(\`✅ Updated', r'console.log(`✅ Updated')
content = content.replace(r'console.log(\`✅ Created', r'console.log(`✅ Created')
content = content.replace(r'body: \`🔗 Synced', r'body: `🔗 Synced')
content = content.replace(r'\${', r'${')

with open(".github/workflows/github-linear-sync.yml", "w") as f:
    f.write(content)

print("Patched.")
