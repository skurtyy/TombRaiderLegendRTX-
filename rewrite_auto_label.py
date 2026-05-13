import sys

content = """name: Reusable - Auto Label Sync

on:
  workflow_call:
    inputs:
      automerge_label:
        required: false
        type: string
        default: automerge
    secrets:
      BOT_TOKEN:
        required: false

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  sync-labels:
    runs-on: ubuntu-latest
    if: github.event_name != 'pull_request_target' || github.event.pull_request.head.repo.full_name == github.repository
    steps:
      - uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.BOT_TOKEN || secrets.GITHUB_TOKEN }}
          script: |
            const labels = [
              { name: "${{ inputs.automerge_label }}", color: "0E8A16", description: "Auto-merge this PR" },
              { name: "dependencies", color: "C2E0C6", description: "Dependency updates" },
              { name: "cursor", color: "1D76DB", description: "Changes from Cursor agent" },
              { name: "claude-review", color: "5319E7", description: "Request a Claude code review" },
              { name: "auto-idea", color: "FBCA04", description: "Auto-generated idea from Claude" },
              { name: "upstream", color: "B60205", description: "Upstream dependency change" },
              { name: "risk-low", color: "C2E0C6", description: "Low risk change (auto-assessed)" },
              { name: "risk-med", color: "FBCA04", description: "Medium risk change (auto-assessed)" },
              { name: "risk-high", color: "B60205", description: "High risk change (auto-assessed)" }
            ];

            for (const label of labels) {
              try {
                await github.rest.issues.getLabel({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  name: label.name
                });
                await github.rest.issues.updateLabel({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  ...label
                });
              } catch (e) {
                await github.rest.issues.createLabel({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  ...label
                });
              }
            }

  label:
    needs: sync-labels
    runs-on: ubuntu-latest
    if: github.event_name != 'pull_request_target' || github.event.pull_request.head.repo.full_name == github.repository
    steps:
      - name: Label Dependabot
        if: ${{ github.actor == 'dependabot[bot]' }}
        uses: actions-ecosystem/action-add-labels@v1
        with:
          github_token: ${{ secrets.BOT_TOKEN || secrets.GITHUB_TOKEN }}
          labels: ${{ inputs.automerge_label }}, dependencies
      - name: Label Cursor branches
        if: ${{ startsWith(github.head_ref || '', 'cursor/') }}
        uses: actions-ecosystem/action-add-labels@v1
        with:
          github_token: ${{ secrets.BOT_TOKEN || secrets.GITHUB_TOKEN }}
          labels: ${{ inputs.automerge_label }}, cursor
      - name: Label Claude branches
        if: ${{ startsWith(github.head_ref || '', 'claude/') }}
        uses: actions-ecosystem/action-add-labels@v1
        with:
          github_token: ${{ secrets.BOT_TOKEN || secrets.GITHUB_TOKEN }}
          labels: ${{ inputs.automerge_label }}
"""

with open(".github/workflows/_auto-label.yml", "w") as f:
    f.write(content)
