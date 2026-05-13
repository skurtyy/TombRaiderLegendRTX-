with open(".github/workflows/_auto-label.yml", "r") as f:
    content = f.read()

old_job = """      - uses: peter-evans/create-or-update-labels@v4
        with:
          token: ${{ secrets.BOT_TOKEN || secrets.GITHUB_TOKEN }}
          labels: |
            - name: ${{ inputs.automerge_label }}
              color: 0E8A16
              description: Auto-merge this PR
            - name: dependencies
              color: C2E0C6
              description: Dependency updates
            - name: cursor
              color: 1D76DB
              description: Changes from Cursor agent
            - name: claude-review
              color: 5319E7
              description: Request a Claude code review
            - name: auto-idea
              color: FBCA04
              description: Auto-generated idea from Claude
            - name: upstream
              color: B60205
              description: Upstream dependency change
            - name: risk-low
              color: C2E0C6
              description: Low risk change (auto-assessed)
            - name: risk-med
              color: FBCA04
              description: Medium risk change (auto-assessed)
            - name: risk-high
              color: B60205
              description: High risk change (auto-assessed)"""

new_job = """      - name: Create or update labels
        env:
          GH_TOKEN: ${{ secrets.BOT_TOKEN || secrets.GITHUB_TOKEN }}
        run: |
          labels=(
            "${{ inputs.automerge_label }}|0E8A16|Auto-merge this PR"
            "dependencies|C2E0C6|Dependency updates"
            "cursor|1D76DB|Changes from Cursor agent"
            "claude-review|5319E7|Request a Claude code review"
            "auto-idea|FBCA04|Auto-generated idea from Claude"
            "upstream|B60205|Upstream dependency change"
            "risk-low|C2E0C6|Low risk change (auto-assessed)"
            "risk-med|FBCA04|Medium risk change (auto-assessed)"
            "risk-high|B60205|High risk change (auto-assessed)"
          )
          for label_info in "${labels[@]}"; do
            name="${label_info%%|*}"
            rest="${label_info#*|}"
            color="${rest%%|*}"
            description="${rest#*|}"
            gh label create "$name" --color "$color" --description "$description" --force || true
          done"""

content = content.replace(old_job, new_job)
with open(".github/workflows/_auto-label.yml", "w") as f:
    f.write(content)
