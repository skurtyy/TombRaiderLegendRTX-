# There is a newer action repository because peter-evans/create-or-update-labels was deleted?
# No, it seems it should be actions/labeler or something? Or maybe we can just remove the sync-labels job entirely if the labels already exist, or change it to github script.
# Wait, let's search if the repository `peter-evans/create-or-update-labels` is real or deprecated?
# No, the github actions runner says: Unable to resolve action peter-evans/create-or-update-labels, repository not found
# Is it `peter-evans/create-or-update-labels` or `peter-evans/create-or-update-comment`? Wait, maybe it's `EndBug/label-sync` ?
# The exact name is `crazy-max/ghaction-github-labeler`?
# No, actually wait. I should just use `gh label create` inside a `run` block because it's much more reliable!
