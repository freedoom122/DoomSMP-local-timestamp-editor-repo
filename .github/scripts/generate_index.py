#!/usr/bin/env python3
"""Rebuild index.json from every dev-local-timestamp-editor-plugin-<ver>.zip in the repo root.
Validates ZIP integrity, manifest id/version vs filename, and dist.script presence."""
import hashlib, json, re, sys, zipfile, pathlib
OWNER_REPO, BRANCH = "freedoom122/DoomSMP-local-timestamp-editor-repo", "main"
BASE = f"https://raw.githubusercontent.com/{OWNER_REPO}/{BRANCH}"
root = pathlib.Path(__file__).resolve().parents[2]
ver_key = lambda v: [int(x) for x in re.split(r"[.-]", v.split("-")[0])] + ([0] if "-" not in v else [-1])
entries, meta, errors = {}, None, []
for z in sorted(root.glob("dev-local-timestamp-editor-plugin-*.zip")):
    ver = z.stem.rsplit("-", 1)[1]
    try:
        with zipfile.ZipFile(z) as zf:
            if zf.testzip(): raise ValueError("corrupt zip")
            m = json.loads(zf.read("manifest.json"))
            if m["version"] != ver: raise ValueError(f"manifest version {m['version']} != filename {ver}")
            if m["dist"]["script"] not in zf.namelist(): raise ValueError("dist.script missing in zip")
    except Exception as e:
        errors.append(f"{z.name}: {e}"); continue
    data = z.read_bytes()
    entries[ver] = {"url": f"{BASE}/{z.name}", "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data), "dependencies": m.get("dependencies", {})}
    if meta is None or ver_key(ver) > ver_key(meta[0]): meta = (ver, m)
if errors or not entries: sys.exit("ERRORS:\n" + "\n".join(errors or ["no zips"]))
ver, m = meta
stable = [v for v in entries if "-" not in v]
channels = {"latest": max(stable, key=ver_key)} if stable else {}
newest = max(entries, key=ver_key)
if newest not in stable and (not stable or ver_key(newest) > ver_key(channels["latest"])): channels["beta"] = newest
icon = m.get("icon", "")
index = {"format": 1, "name": "Local Timestamp Editor",
         "description": "Local-only per-message timestamp overrides for Revenge.",
         "plugins": {m["id"]: {"name": m["name"], "description": m["description"], "author": m["author"],
                               **({"icon": icon} if icon.startswith("data:") else {}),
                               "channels": channels,
                               "versions": dict(sorted(entries.items(), key=lambda kv: ver_key(kv[0])))}}}
(root / "index.json").write_text(json.dumps(index, indent=2) + "\n")
print("index.json written:", channels, list(entries))
