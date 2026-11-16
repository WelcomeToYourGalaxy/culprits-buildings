# culprits-buildings

The buildings the Culprits map draws: banks, police stations, courthouses,
town halls, prisons, embassies and the rest, one archive per kind, with the
places each source file describes merged into one record per place.

- `tiles/building_types.json` — every kind, how many places it holds, and the
  file that holds it. The map reads this first.
- `tiles/buildings/<kind>.pmtiles` — one kind, loaded when that kind is ticked.

Rebuilt every Monday by `.github/workflows/refresh.yml`, from the same source
files the map's own pipeline uses (`pipeline/building_types.py` in
[culprits](https://github.com/WelcomeToYourGalaxy/culprits)). Nothing is
dropped in the merge: every source row ends up in exactly one record, and each
record lists the files that describe it.

These files live here rather than in `culprits-tiles-more` because a GitHub
Pages site is capped at 1 GB and these are about 700 MB of it. Each save
replaces the history with a single commit, so the repo stays the size of what
it publishes.
