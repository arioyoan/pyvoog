"""
status.py — Show site info, git state, and file counts.
"""

import os

from . import git
from .manifest import load as load_manifest


def status(site_dir, config, out):
    """Print site status to out."""
    out.info(f"Site:      {config.host}")
    out.info(f"Protocol:  {config.protocol}")
    out.info(f"Directory: {site_dir}")

    # -- Manifest info -------------------------------------------------

    manifest = load_manifest(site_dir)
    if manifest:
        layouts = manifest.get("layouts", [])
        assets = manifest.get("assets", [])
        components = [l for l in layouts if l.get("component")]
        page_layouts = [l for l in layouts if not l.get("component")]
        out.info(f"\nManifest (manifest.json):")
        out.info(f"  Layouts:    {len(page_layouts)}")
        out.info(f"  Components: {len(components)}")
        out.info(f"  Assets:     {len(assets)}")
    else:
        out.info("\nManifest: not found (run  voog pull  to create it)")

    # -- Git info ------------------------------------------------------

    git_dir = os.path.join(site_dir, ".git")
    if not os.path.isdir(git_dir):
        out.info("\nGit: not initialised (will be set up on first pull)")
    elif not git.git_available():
        out.info("\nGit: git binary not found on PATH")
    else:
        last = git.last_commit_info(site_dir)
        if last:
            out.info(f"\nGit: {last['hash']}  {last['date'][:19]}")
            out.info(f"     {last['message']}")
        else:
            out.info("\nGit: repo exists but no commits yet")

        if git.has_changes(site_dir):
            out.info("     (uncommitted local changes — run  git diff  to review)")
