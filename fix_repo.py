with open(".github/workflows/_auto-label.yml", "r") as f:
    content = f.read()

# I need to explicitly pass repo via GH_REPO env or the `gh` command needs to know the repo context.
# GitHub Actions usually runs inside the checked out repository. BUT! We don't have an `actions/checkout` step in the `sync-labels` job!
# So `gh` does not know which repo it is in!
# That's why we need to pass `--repo $GITHUB_REPOSITORY` to `gh label create` OR add an `actions/checkout` step.

old_run = """            gh label create "$name" --color "$color" --description "$description" --force || true"""
new_run = """            gh label create "$name" --color "$color" --description "$description" --repo "$GITHUB_REPOSITORY" --force || true"""

content = content.replace(old_run, new_run)
with open(".github/workflows/_auto-label.yml", "w") as f:
    f.write(content)
