#!/usr/bin/env bash
set -euo pipefail

# Build the Hugo site locally and publish it to the gh-pages branch.
# Requirements:
#   - Hugo installed locally
#   - A remote named "origin" pointing at the GitHub repo
#   - The gh-pages branch either existing remotely or allowed to be created

BUILD_DIR="public"
WORKTREE_DIR="../.gh-pages"
BRANCH="gh-pages"

# Build the site
HUGO_CACHEDIR="$(pwd)/.hugo_cache" hugo --gc --minify

# Prepare gh-pages worktree
if [ ! -d "$WORKTREE_DIR" ]; then
  git worktree add -B "$BRANCH" "$WORKTREE_DIR" "origin/$BRANCH" || git worktree add -B "$BRANCH" "$WORKTREE_DIR"
fi

# Sync build output
rsync -av --delete "$BUILD_DIR"/ "$WORKTREE_DIR"/

# Commit and push
pushd "$WORKTREE_DIR" >/dev/null
if [ -n "$(git status --porcelain)" ]; then
  git add --all
  git commit -m "Publish site"
  git push origin "$BRANCH"
else
  echo "No changes to deploy"
fi
popd >/dev/null

