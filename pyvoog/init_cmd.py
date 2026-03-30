"""
init_cmd.py — Initialise a new Voog site directory.

Creates:
  <dir>/.voog        — site config (host, api_token)
  <dir>/.gitignore   — excludes .voog token from git
  <dir>/             — git init

Existing directories are supported (add .voog to an existing clone).
"""

import os

from .config import write_voog_file, load_config, ConfigError
from . import git


SITE_GITIGNORE = """\
# pyvoog — auto-generated .gitignore

# API token — never commit this
.voog

# Node / build tools
node_modules/
dist/
build/
.cache/

# Python cache
__pycache__/
*.pyc

# OS
.DS_Store
Thumbs.db
"""


def init(target_dir, host, api_token, protocol="https", out=None):
    """
    Initialise a site directory.

    target_dir — directory to initialise (created if it doesn't exist)
    host       — e.g. 'mysite.voog.com'
    api_token  — Voog API token
    protocol   — 'https' (default) or 'http'

    Returns True on success. Prints progress via out (Output instance).
    """
    abs_dir = os.path.abspath(target_dir)

    # -- Create directory if needed ------------------------------------

    if not os.path.exists(abs_dir):
        os.makedirs(abs_dir)
        out and out.info(f"Created directory: {abs_dir}")
    else:
        out and out.info(f"Using directory:   {abs_dir}")

    # -- Write .voog ---------------------------------------------------

    voog_path = os.path.join(abs_dir, ".voog")
    if os.path.isfile(voog_path):
        out and out.warn(f".voog already exists, not overwriting: {voog_path}")
    else:
        write_voog_file(voog_path, host, api_token, protocol=protocol)
        out and out.info(f"Created .voog (keep this file private — it contains your API token)")

    # -- Write .gitignore ----------------------------------------------

    gitignore_path = os.path.join(abs_dir, ".gitignore")
    if os.path.isfile(gitignore_path):
        out and out.log(".gitignore already exists, not overwriting.")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(SITE_GITIGNORE)
        out and out.info("Created .gitignore")

    # -- Git init ------------------------------------------------------

    if not git.git_available():
        out and out.warn("git not found on PATH — skipping git init. Install git for undo support.")
    else:
        try:
            initialised = git.ensure_repo(abs_dir)
            if initialised:
                out and out.info("Initialised git repository.")
            else:
                out and out.log("Git repository already exists.")
        except RuntimeError as exc:
            out and out.warn(f"git init failed: {exc}")

    # -- Verify config is readable -------------------------------------

    try:
        cfg = load_config(site_dir=abs_dir)
        out and out.info(f"\nReady. Site: {cfg.host}")
        out and out.info("Run  pyvoog pull  to download all templates and assets.")
    except ConfigError as exc:
        out and out.error(f"Config verification failed: {exc}")
        return False

    return True
