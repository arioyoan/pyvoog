"""
api.py — Voog REST API client.

Authentication: X-API-Token header (read from .voog).
All requests use urllib.request (stdlib only, no dependencies).

Key endpoints used:
  GET /admin/api/layouts?per_page=250
  GET /admin/api/assets?per_page=250&page=N
"""

import json
import time
import urllib.error
import urllib.request


class APIError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class VoogAPI:
    def __init__(self, config, output=None):
        """
        config  — SiteConfig instance
        output  — Output instance (for logging); may be None
        """
        self._config = config
        self._out = output

    def _log(self, msg):
        if self._out:
            self._out.log(msg)

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    def _get(self, path, binary=False, _retry=1):
        """
        Perform authenticated GET request.

        path    — API path (e.g. '/admin/api/layouts?per_page=250')
        binary  — if True, return raw bytes; else parse as JSON
        _retry  — internal; number of retries left on network error
        """
        url = f"{self._config.base_url}{path}"
        self._log(f"GET {url}")
        req = urllib.request.Request(
            url,
            headers={"X-API-Token": self._config.api_token},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return raw if binary else json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise APIError(
                    "Authentication failed (401). "
                    "Check api_token in your .voog file.",
                    status_code=401,
                )
            if exc.code == 404:
                raise APIError(
                    f"Not found (404): {url}",
                    status_code=404,
                )
            raise APIError(f"HTTP {exc.code} for {url}", status_code=exc.code)
        except urllib.error.URLError as exc:
            if _retry > 0:
                self._log(f"Network error ({exc.reason}), retrying in 2s…")
                time.sleep(2)
                return self._get(path, binary=binary, _retry=_retry - 1)
            raise APIError(f"Network error: {exc.reason}")

    def _download(self, url, _retry=1):
        """Download a binary resource from an arbitrary URL (no auth required)."""
        self._log(f"GET {url}")
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.URLError as exc:
            if _retry > 0:
                self._log(f"Network error ({exc.reason}), retrying in 2s…")
                time.sleep(2)
                return self._download(url, _retry=_retry - 1)
            raise APIError(f"Failed to download {url}: {exc.reason}")

    # ------------------------------------------------------------------
    # Layouts
    # ------------------------------------------------------------------

    def get_layouts(self):
        """
        Return all layouts/components for this site (list only, no body).
        Single call using per_page=250 (Voog max).
        """
        return self._get("/admin/api/layouts?per_page=250")

    def get_layout(self, layout_id):
        """Fetch a single layout by ID, including its body content."""
        return self._get(f"/admin/api/layouts/{layout_id}")

    def update_layout(self, layout_id, body):
        """
        Push new body content to a layout via PUT.
        Returns the updated layout dict from the server.
        """
        return self._put(f"/admin/api/layouts/{layout_id}", {"body": body})

    def _put(self, path, data, _retry=1):
        """Perform an authenticated PUT request with a JSON body."""
        url = f"{self._config.base_url}{path}"
        self._log(f"PUT {url}")
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "X-API-Token": self._config.api_token,
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise APIError(
                    "Authentication failed (401). "
                    "Check api_token in your .voog file.",
                    status_code=401,
                )
            if exc.code == 404:
                raise APIError(
                    f"Not found (404): {url}",
                    status_code=404,
                )
            raise APIError(f"HTTP {exc.code} for {url}", status_code=exc.code)
        except urllib.error.URLError as exc:
            if _retry > 0:
                self._log(f"Network error ({exc.reason}), retrying in 2s\u2026")
                time.sleep(2)
                return self._put(path, data, _retry=_retry - 1)
            raise APIError(f"Network error: {exc.reason}")

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------

    def get_layout_assets(self):
        """
        Return all layout/design assets (CSS, JS, images, fonts).

        Uses /admin/api/layout_assets — these are the design template assets,
        NOT media library uploads (which live at /admin/api/assets).
        """
        assets = []
        page = 1
        while True:
            page_data = self._get(f"/admin/api/layout_assets?per_page=250&page={page}")
            if not page_data:
                break
            assets.extend(page_data)
            if len(page_data) < 250:
                break
            page += 1
        return assets

    def get_layout_asset(self, asset_id):
        """Fetch a single layout asset by ID (text assets include 'data' field)."""
        return self._get(f"/admin/api/layout_assets/{asset_id}")

    def update_layout_asset(self, asset_id, data):
        """
        Push new text content to a layout asset (CSS/JS) via PUT.
        Returns the updated asset dict from the server.
        """
        return self._put(f"/admin/api/layout_assets/{asset_id}", {"data": data})

    def download_url(self, url):
        """Download binary content from a public URL (no auth needed)."""
        return self._download(url)
