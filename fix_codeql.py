with open(".github/workflows/_codeql.yml", "r") as f:
    content = f.read()

# Wait, the failure is:
# "Code Scanning could not process the submitted SARIF file: CodeQL analyses from advanced configurations cannot be processed when the default setup is enabled"
# This happens when both GitHub's default CodeQL setup is enabled on the repository settings, AND there's a custom codeql action in the workflow.
# Since we have `github/codeql-action`, we shouldn't have Default Setup enabled, OR we should remove the custom workflow if we want to rely on Default Setup.
# Wait, if we can't change repo settings, maybe we should just delete the codeql.yml workflow, or disable it.
# Is the workflow expected to run? It's a reusable workflow called by `.github/workflows/codeql.yml`?
