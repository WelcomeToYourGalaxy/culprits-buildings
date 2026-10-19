#!/usr/bin/env bash
# Commits what the build made and publishes it, keeping this repo the size of
# what it publishes rather than the sum of every week's copies.
#
# The archives are rebuilt whole each week, about 700 MB of them. Kept as
# ordinary commits, a year of rebuilds would be tens of gigabytes of old
# copies nobody reads, and every checkout would pay for them. So each save
# replaces the history with a single commit holding the current files. The
# scripts and this workflow are in that commit too - they are in the working
# tree, so nothing is lost.
#
# Files over 95 MB are left out (GitHub refuses files over 100 MB) and named
# in the log.
set -u
msg="$1"
git config user.name "culprits-buildings"
git config user.email "actions@users.noreply.github.com"
find . -path ./.git -prune -o -type f -size +99614720c -print | while IFS= read -r f; do
  echo "$f is over 95 MB; left out."
  rm -f "$f"
done
git checkout -q --orphan rebuilt
git add -A
git commit -q -m "$msg"
git branch -M rebuilt main
# A rebuild that produced exactly what is already published is not pushed, so
# an unchanged week costs nothing.
git fetch -q origin main || true
if [ "$(git rev-parse main^{tree})" = "$(git rev-parse FETCH_HEAD^{tree} 2>/dev/null || echo none)" ]; then
  echo "Nothing changed."
  exit 0
fi
for i in 1 2 3 4 5; do
  if git push -q -f origin main; then
    echo "Saved."
    gh api -X POST "repos/$REPO/pages/builds" >/dev/null 2>&1 || echo "Pages will republish on its own."
    exit 0
  fi
  echo "Push attempt $i did not go through; trying again."
  sleep $((RANDOM % 20 + 5))
done
echo "Could not push after 5 tries."
exit 1
