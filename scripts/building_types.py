#!/usr/bin/env python3
"""
Buildings: one archive per kind of building, plus a summary the map reads.

Builds tiles/buildings/<kind>.pmtiles and tiles/building_types.json from the
accountability maps' building files, with duplicate places merged, using the
culprits repo's own pipeline/building_types.py. Nothing is dropped: every
source row ends up in exactly one output record, and each record lists all the
files that describe it.

This repo exists because a GitHub Pages site is capped at 1 GB and these
archives are about 700 MB of it. They were in culprits-tiles-more, which passed
the cap once they landed there; here they have a site of their own.

Runs weekly (Mondays), when the workflow is run by hand, or when not yet built.
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile, time

DIR = pathlib.Path("tiles/buildings")
SUMMARY = pathlib.Path("tiles/building_types.json")
CULPRITS = "https://github.com/WelcomeToYourGalaxy/culprits.git"
LIMIT = 95 * 1024 * 1024          # GitHub refuses files over 100 MB


def sh(*cmd, **kw):
    print("  $", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def tools():
    """tippecanoe, built from source; the runner has no package for it."""
    if not shutil.which("tippecanoe"):
        sh("sudo", "apt-get", "update", "-qq")
        sh("sudo", "apt-get", "install", "-y", "-qq", "libsqlite3-dev", "zlib1g-dev", "build-essential")
        d = tempfile.mkdtemp()
        sh("git", "clone", "--depth", "1", "https://github.com/felt/tippecanoe.git", d)
        sh("make", "-j4", cwd=d)
        sh("sudo", "make", "install", cwd=d)


def main():
    weekly = time.gmtime().tm_wday == 0 or os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch") == "workflow_dispatch"
    if DIR.exists() and any(DIR.glob("*.pmtiles")) and not weekly:
        print("buildings: rebuilt weekly; not today")
        return
    tools()
    work = pathlib.Path(tempfile.mkdtemp())
    sh("git", "clone", "--depth", "1", CULPRITS, str(work / "culprits"))
    sh(sys.executable, "-m", "pip", "install", "-q", "requests")
    pts = work / "buildings.geojsonl"
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    sh(sys.executable, str(work / "culprits/pipeline/building_types.py"), str(pts), str(SUMMARY.resolve()),
       cwd=str(work / "culprits/pipeline"))
    # One archive per kind. All kinds in one archive came out over GitHub's
    # 100 MB limit even at zoom 9, so nothing was published and the layer drew
    # nothing. Split, each kind fits, and the map loads only what is ticked.
    per = {}
    with open(pts, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            t = json.loads(line).get("properties", {}).get("type") or "Other"
            per.setdefault(t, []).append(line)
    DIR.mkdir(parents=True, exist_ok=True)
    files, failed = {}, []
    for t, lines in sorted(per.items()):
        slug = re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_") or "other"
        src = work / f"{slug}.geojsonl"
        src.write_text("".join(lines), encoding="utf-8")
        tmp = work / f"{slug}.pmtiles"
        for maxz in (14, 13, 12, 11, 10, 9):
            sh("tippecanoe", "-o", str(tmp), "--force", "-q", "-Z0", f"-z{maxz}", "-l", "buildings", "-P",
               "--drop-densest-as-needed", "--extend-zooms-if-still-dropping", "-r1", str(src))
            if tmp.stat().st_size <= LIMIT:
                break
        else:
            failed.append(t)
            continue
        shutil.move(str(tmp), str(DIR / f"{slug}.pmtiles"))
        files[t] = f"buildings/{slug}.pmtiles"
        print(f"  {t}: {len(lines):,} places, {(DIR / f'{slug}.pmtiles').stat().st_size / 1e6:.1f} MB")
    # A kind that failed this time keeps the copy already published, so a bad
    # run cannot empty the map: its file is still there and still listed.
    for t in failed:
        slug = re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_") or "other"
        if (DIR / f"{slug}.pmtiles").exists():
            files[t] = f"buildings/{slug}.pmtiles"
            print(f"  {t}: over the limit this run; the published copy stays")
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary["files"] = files
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"buildings: {len(files)} kinds in {DIR}/" + (f"; over the limit: {failed}" if failed else ""))
    if not files:
        sys.exit("buildings: no kind could be built")


if __name__ == "__main__":
    main()
