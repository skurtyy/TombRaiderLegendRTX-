with open(".github/workflows/_auto-label.yml", "r") as f:
    content = f.read()

# I see what's happening. In `.github/workflows/_auto-label.yml`, the `label` job ALSO uses an action!
# Wait, the failure is "Unable to resolve action peter-evans/create-or-update-labels, repository not found"
# The label job uses `actions-ecosystem/action-add-labels@v1`.
# Oh! Wait, did I leave a reference to peter-evans? Let's check `grep -rn peter-evans`
