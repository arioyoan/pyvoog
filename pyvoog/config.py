"""
config.py — Load and validate the .voog site configuration file.

The .voog file uses INI-style format (same as the Ruby voog-kit):

    [site.voog.com]
    host=site.voog.com
    api_token=abc123
    protocol=https
    overwrite=true

Multiple sections = multiple sites; use --site to select one.
"""

import os
import configparser


class ConfigError(Exception):
    pass


class SiteConfig:
    def __init__(self, section, host, api_token, protocol="https"):
        self.section = section
        self.host = host
        self.api_token = api_token
        self.protocol = protocol

    @property
    def base_url(self):
        return f"{self.protocol}://{self.host}"

    def __repr__(self):
        return f"<SiteConfig host={self.host!r}>"


def find_voog_file(start_dir=None):
    """
    Walk upward from start_dir (default: cwd) looking for a .voog file.
    Returns the absolute path if found, else None.
    """
    d = os.path.abspath(start_dir or os.getcwd())
    while True:
        candidate = os.path.join(d, ".voog")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_config(site_dir=None, site_name=None):
    """
    Load .voog config.

    site_dir  — where to start searching (default: cwd)
    site_name — which section to use if .voog has multiple sites

    Raises ConfigError with a helpful message on any problem.
    """
    voog_file = find_voog_file(site_dir)
    if not voog_file:
        raise ConfigError(
            "No .voog config file found in this directory (or any parent).\n"
            "Run  pyvoog init --host <host> --token <token>  to set up a site here."
        )

    cp = configparser.ConfigParser()
    cp.read(voog_file, encoding="utf-8")

    sections = cp.sections()
    if not sections:
        raise ConfigError(
            f".voog file has no sections: {voog_file}\n"
            "Expected format:\n"
            "  [site.voog.com]\n"
            "  host=site.voog.com\n"
            "  api_token=<your-token>"
        )

    if site_name:
        section = None
        for s in sections:
            if s == site_name or cp[s].get("host", "") == site_name:
                section = s
                break
        if not section:
            available = ", ".join(sections)
            raise ConfigError(
                f"Site '{site_name}' not found in {voog_file}.\n"
                f"Available sections: {available}"
            )
    else:
        section = sections[0]

    cfg = cp[section]

    host = cfg.get("host", section)
    api_token = cfg.get("api_token", "").strip()
    if not api_token:
        raise ConfigError(
            f"No api_token in .voog section [{section}].\n"
            "Add:  api_token=<your-token>"
        )

    return SiteConfig(
        section=section,
        host=host,
        api_token=api_token,
        protocol=cfg.get("protocol", "https"),
    )


def write_voog_file(path, host, api_token, protocol="https"):
    """Write a .voog config file."""
    content = (
        f"[{host}]\n"
        f"host={host}\n"
        f"api_token={api_token}\n"
        f"protocol={protocol}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
