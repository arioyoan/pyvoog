"""
git.py — Lightweight git integration for voog-cli.

Provides auto-init and auto-commit so every pull is a reversible snapshot.
All operations call the system `git` binary via subprocess.
Git is optional — the tool works without it, but warns.
"""

import os
import shutil
import subprocess


def git_available():
    """Return True if the `git` binary is on PATH."""
    return shutil.which("git") is not None


def _git(*args, cwd=None):
    """
    Run git with the given args in cwd.
    Returns (returncode, stdout, stderr).
    Never raises — callers check returncode.
    """
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ensure_repo(path):
    """
    Ensure path is a git repository.
    If .git doesn't exist, runs `git init`.
    Returns True if a new repo was initialised, False if it already existed.
    Raises RuntimeError on failure.
    """
    if os.path.isdir(os.path.join(path, ".git")):
        return False

    code, _, err = _git("init", cwd=path)
    if code != 0:
        raise RuntimeError(f"git init failed: {err}")
    return True


def has_changes(path):
    """Return True if there are staged or unstaged changes in the repo."""
    _code, out, _err = _git("status", "--porcelain", cwd=path)
    return bool(out.strip())


def commit_all(path, message):
    """
    Stage all changes (git add -A) and commit with message.
    Returns True if a commit was made, False if there was nothing to commit.
    Raises RuntimeError on commit failure.
    """
    if not has_changes(path):
        return False

    _git("add", "-A", cwd=path)
    code, _out, err = _git("commit", "-m", message, cwd=path)
    if code != 0:
        raise RuntimeError(f"git commit failed: {err}")
    return True


def last_commit_info(path):
    """
    Return a dict with last commit info, or None if no commits yet.
    Keys: hash (short), message, date.
    """
    code, out, _err = _git(
        "log", "-1", "--pretty=format:%h|%s|%ci", cwd=path
    )
    if code != 0 or not out:
        return None
    parts = out.split("|", 2)
    if len(parts) < 3:
        return None
    return {"hash": parts[0], "message": parts[1], "date": parts[2]}



def changed_files(path):
    """
    Return all files changed since the last commit (working tree vs HEAD),
    regardless of extension or directory.
    Returns an empty list if there is no git repo or no commits yet.
    """
    code, out, _err = _git("diff", "HEAD", "--name-only", cwd=path)
    if code != 0 or not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_files(path, files, message):
    """
    Stage only the specified files and commit.

    files   — iterable of relative paths within the repo
    message — commit message

    Unlike commit_all(), this never stages files outside the given list,
    so developer files in the same directories are left untracked.

    Returns True if a commit was made, False if nothing to commit.
    Raises RuntimeError on failure.
    """
    for f in files:
        _git("add", f, cwd=path)

    # Check if anything is actually staged
    code, _out, _err = _git("diff", "--cached", "--quiet", cwd=path)
    if code == 0:
        return False  # nothing staged

    code, _out, err = _git("commit", "-m", message, cwd=path)
    if code != 0:
        raise RuntimeError(f"git commit failed: {err}")
    return True

