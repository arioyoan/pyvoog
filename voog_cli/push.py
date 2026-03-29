"""
push.py — Push locally modified layouts and text assets to the Voog server.

Change detection:  git diff HEAD filtered against manifest.json entries.
Conflict detection: server updated_at vs manifest updated_at — if the server
                    was modified after our last pull, we skip and warn.

Safety rules:
  - Only files present in manifest.json are eligible for push.
    Developer files in the same directories are silently ignored.
  - Binary assets (images/fonts) cannot be updated via the API; skipped.
  - Creating new remote files is not yet supported; files absent from the
    server get a clear error with a suggested remedy.
"""

import os

from .api import APIError
from .manifest import load, lookup_by_file, layout_file_path, asset_file_path
from . import git


TEXT_ASSET_TYPES = frozenset(("stylesheet", "javascript"))


def push(api, site_dir, files=None, dry_run=False, out=None):
    """
    Push locally modified files to the Voog server.

    api      — VoogAPI instance
    site_dir — absolute path to the site directory
    files    — optional list of specific relative paths to push;
               if None, candidates are determined by git diff HEAD
    dry_run  — show what would be pushed but don't upload

    Only files that appear in manifest.json are pushed.
    Returns (succeeded, failed) lists of relative paths.
    """
    succeeded = []
    failed = []

    # -- Load manifest ------------------------------------------------

    manifest = load(site_dir)
    if not manifest:
        out and out.error(
            "No manifest.json found. Run 'voog pull' first to sync the site."
        )
        return succeeded, failed

    by_file = lookup_by_file(manifest)  # {rel_path: entry}

    if not by_file:
        out and out.info("Manifest is empty — nothing to push.")
        return succeeded, failed

    # -- Determine candidates -----------------------------------------

    if files:
        # Explicit file list from the command line
        candidates = []
        for f in files:
            f = f.replace("\\", "/")  # normalise Windows paths
            if f in by_file:
                candidates.append(f)
            else:
                out and out.warn(
                    f"{f}: not in manifest — skipping. "
                    "The file may not exist on the server, or run 'voog pull' first."
                )
    else:
        # git diff HEAD ∩ manifest
        if not git.git_available():
            out and out.error(
                "git is not available — cannot detect changed files. "
                "Specify files explicitly: voog push layouts/page.tpl"
            )
            return succeeded, failed

        changed = git.changed_files(site_dir)
        candidates = [f for f in changed if f in by_file]

        # Log skipped developer files (verbose only)
        skipped_dev = [
            f for f in changed
            if f not in by_file and f != "manifest.json"
        ]
        if skipped_dev:
            out and out.log(
                f"  ({len(skipped_dev)} non-manifest file(s) skipped: "
                + ", ".join(skipped_dev[:3])
                + ("…" if len(skipped_dev) > 3 else "") + ")"
            )

    if not candidates:
        out and out.info(
            "Nothing to push — no local changes to manifest-tracked files."
        )
        return succeeded, failed

    prefix = "[dry-run] " if dry_run else ""
    out and out.info(f"{prefix}{len(candidates)} file(s) to push:")
    for f in candidates:
        out and out.info(f"  ~ {f}")
    out and out.info("")

    # -- Fetch server state for conflict detection --------------------
    #
    # We fetch the full layout/asset lists (lightweight — no bodies).
    # This gives us the current server updated_at and the server IDs.
    # We compare server updated_at vs the updated_at stored in our manifest
    # (recorded at last pull) to detect if someone edited on the server.

    out and out.info("Checking server state…")

    has_layouts = any(f.startswith(("layouts/", "components/")) for f in candidates)
    has_assets  = any(not f.startswith(("layouts/", "components/")) for f in candidates)

    server_by_file = {}  # {rel_path: {"id": int, "updated_at": str}}

    if has_layouts:
        try:
            for lay in api.get_layouts():
                name      = lay.get("layout_name", "")
                component = lay.get("component", False)
                fp = layout_file_path(name, component)
                server_by_file[fp] = {
                    "id":         lay["id"],
                    "updated_at": lay.get("updated_at", ""),
                }
        except APIError as exc:
            out and out.error(f"Could not fetch layouts from server: {exc}")
            return succeeded, failed

    if has_assets:
        try:
            for asset in api.get_layout_assets():
                fp = asset_file_path(
                    asset.get("filename", ""), asset.get("asset_type", "")
                )
                server_by_file[fp] = {
                    "id":         asset["id"],
                    "updated_at": asset.get("updated_at", ""),
                }
        except APIError as exc:
            out and out.error(f"Could not fetch assets from server: {exc}")
            return succeeded, failed

    # -- Push each file -----------------------------------------------

    total        = len(candidates)
    conflicts    = []
    manifest_dirty = False

    for i, rel_path in enumerate(candidates, 1):
        entry       = by_file[rel_path]
        server_info = server_by_file.get(rel_path)

        out and out.progress(i, total, rel_path)

        # File in manifest but absent on server
        if server_info is None:
            out and out.progress_done()
            out and out.warn(
                f"{rel_path}: not found on server. "
                "Creating new files is not yet supported — "
                "create it via the Voog editor first, then run 'voog pull'."
            )
            failed.append((rel_path, "not on server"))
            continue

        # Conflict check: has the server been edited since our last pull?
        manifest_ts = entry.get("updated_at", "")
        server_ts   = server_info.get("updated_at", "")
        if manifest_ts and server_ts and manifest_ts != server_ts:
            out and out.progress_done()
            out and out.warn(
                f"{rel_path}: CONFLICT — server was modified after last pull "
                f"(pulled: {manifest_ts[:10]}, server now: {server_ts[:10]}). "
                "Skipping. Run 'voog pull' to sync server changes first."
            )
            conflicts.append(rel_path)
            failed.append((rel_path, "conflict"))
            continue

        if dry_run:
            succeeded.append(rel_path)
            continue

        # Read local content
        abs_path = os.path.join(site_dir, rel_path)
        try:
            with open(abs_path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            out and out.progress_done()
            out and out.warn(f"Could not read {rel_path}: {exc}")
            failed.append((rel_path, str(exc)))
            continue

        # Upload
        is_layout  = rel_path.startswith(("layouts/", "components/"))
        asset_type = entry.get("asset_type", "")
        try:
            if is_layout:
                resp = api.update_layout(server_info["id"], content)
            elif asset_type in TEXT_ASSET_TYPES:
                resp = api.update_layout_asset(server_info["id"], content)
            else:
                # Binary assets (image, font, svg…) cannot be updated in-place
                out and out.progress_done()
                out and out.warn(
                    f"{rel_path}: binary assets cannot be pushed "
                    "(images/fonts must be updated via the Voog editor)."
                )
                failed.append((rel_path, "binary asset"))
                continue

            # Capture the new server timestamp so next push doesn't conflict
            new_ts = (resp or {}).get("updated_at", "")
            if new_ts:
                entry["updated_at"] = new_ts
                manifest_dirty = True

            succeeded.append(rel_path)

        except APIError as exc:
            out and out.progress_done()
            out and out.warn(f"Failed to push {rel_path}: {exc}")
            failed.append((rel_path, str(exc)))

    out and out.progress_done()

    # -- Save manifest + auto-commit pushed files ---------------------

    if not dry_run and succeeded:
        # Write back any updated_at timestamps the server returned
        if manifest_dirty:
            from .manifest import save as save_manifest
            try:
                save_manifest(manifest, site_dir)
                out and out.log("Updated manifest.json with new server timestamps.")
            except OSError as exc:
                out and out.warn(f"Could not update manifest.json: {exc}")

        if git.git_available():
            try:
                git.ensure_repo(site_dir)
                commit_paths = list(succeeded)
                if manifest_dirty:
                    commit_paths.append("manifest.json")
                committed = git.commit_files(
                    site_dir,
                    commit_paths,
                    f"voog push: {len(succeeded)} file(s)",
                )
                if committed:
                    out and out.info(
                        f"\nCommitted {len(succeeded)} pushed file(s) to git."
                    )
                else:
                    out and out.log("Nothing new to commit in git after push.")
            except RuntimeError as exc:
                out and out.warn(f"Git commit after push failed: {exc}")

    # -- Summary ------------------------------------------------------

    if dry_run:
        out and out.info(f"[dry-run] Would push {len(succeeded)} file(s).")
    else:
        out and out.summary(succeeded, failed)
        if conflicts:
            out and out.info(
                f"\n{len(conflicts)} conflict(s) skipped — "
                "run 'voog pull' to sync server changes first."
            )

    return succeeded, failed
