# voog-cli

> **Work in progress** — has not been tested end-to-end in all scenarios. Issues and feedback are welcome.

A Python replacement for the Ruby [voog-kit](https://github.com/Voog/voog-kit).  
Manage Voog CMS site templates and design assets directly via the REST API.

**Why?**

- **Fixes the hyphen bug** — the Ruby kit silently fails to pull any layout whose `layout_name` contains hyphens, a common naming pattern. This tool calls the API directly, so every file is handled correctly.
- **Proper git tracking** — every pull and push is automatically committed to git, giving you real diff history, easy rollback, and change detection for push.
- **No Ruby required** — no gem/bundle/rbenv toolchain needed. Just Python 3.11+ (stdlib only, zero dependencies). Works on Windows and macOS.

---

## Features

- **Pull** all layouts, components, CSS, JS, images and fonts in one command
- **Push** locally modified files back to the server (layouts + text assets)
- **Conflict detection** — push warns when the server has changed since your last pull
- **Manifest-scoped git** — only Voog-tracked files are committed; developer files are ignored
- `voog check` compares local files against the server without changing anything
- `voog manifest` inspects the remote file structure
- Partial pulls: `voog pull layouts` or `voog pull assets`
- Dry-run mode for both pull and push
- Multi-site support via `--site` flag

---

## Installation

1. **Clone this repo** into any directory (it lives separately from your site repos):

   ```bash
   git clone https://github.com/Voog/voog-cli.git
   ```

2. **Set up a shell alias** (optional but recommended):

   **Windows (PowerShell profile)**:
   ```powershell
   function voog { python "C:\path\to\voog-cli\voog.py" @args }
   ```

   **macOS / Linux (~/.bashrc or ~/.zshrc)**:
   ```bash
   alias voog="python ~/path/to/voog-cli/voog.py"
   ```

3. **Python 3.11+** must be on your PATH. Verify: `python --version`

---

## Quick start

```bash
# 1. Create a new site directory
voog init ./my-site --host mysite.voog.com --token YOUR_API_TOKEN

# 2. Pull everything
cd ./my-site
voog pull

# 3. Edit files locally, then push changes
voog push

# 4. Check sync status at any time
voog check
```

### Adding voog-cli to an existing site directory

```bash
cd /path/to/existing-site
voog init --host mysite.voog.com --token YOUR_API_TOKEN
voog pull
```

---

## Commands

### `voog init [DIR] --host HOST --token TOKEN`

Initialise a site directory.

```bash
voog init --host mysite.voog.com --token abc123
voog init ./my-site --host mysite.voog.com --token abc123
```

Creates:
- `.voog` — site config (kept out of git via `.gitignore`)
- `.gitignore` — excludes `.voog` and cache files
- `.git/` — git repository (for undo/history)

---

### `voog pull [layouts|assets] [--dry-run] [--reset]`

Pull files from the server. The server is always the source of truth.

```bash
voog pull                  # pull everything (layouts + assets)
voog pull layouts          # only .tpl files (layouts + components)
voog pull assets           # only CSS, JS, images, fonts
voog pull --dry-run        # see what would change, without writing
voog pull --reset          # also remove orphaned local .tpl files
```

After a successful pull, changed files are automatically committed to git.
Only manifest-tracked files are staged — developer files in the same directories are left untouched.

---

### `voog push [FILE ...] [--dry-run]`

Push locally modified files to the server.

```bash
voog push                              # push all changed manifest-tracked files
voog push layouts/page.tpl             # push a specific file
voog push stylesheets/main.css         # push a CSS file
voog push --dry-run                    # see what would be pushed
```

**How push works:**

1. Detects changed files via `git diff HEAD`
2. Filters to only files present in `manifest.json` (developer files are ignored)
3. Checks the server for conflicts (`updated_at` comparison)
4. Uploads safe files; warns and skips conflicting ones
5. Auto-commits pushed files to git

**What can be pushed:**
- Layouts and components (`.tpl` files)
- Text assets: CSS and JavaScript files

**Not supported (yet):**
- Binary assets (images, fonts) — these must be uploaded via the Voog editor
- Creating new files on the server — create them in Voog first, then `voog pull`

---

### `voog check`

Compare local files against the server without changing anything.

```bash
voog check
voog check --verbose
```

Reports:
- **Missing** — on server, not local
- **Modified** — local file differs from server
- **Extra** — local file, not on server
- **In sync** — matches server exactly

---

### `voog manifest [--save]`

Fetch and display the remote file structure.

```bash
voog manifest              # show summary
voog manifest --verbose    # show full file list
voog manifest --save       # write manifest.json to site directory
```

---

### `voog status`

Show site info, manifest summary, and last git commit.

```bash
voog status
```

---

### `voog help [command]`

```bash
voog help
voog help pull
voog help push
```

---

## .voog config format

The `.voog` file is INI-style, compatible with the Ruby voog-kit:

```ini
[mysite.voog.com]
host=mysite.voog.com
api_token=your_api_token_here
protocol=https
```

**Never commit `.voog` — it contains your API token.** The `voog init` command adds it to `.gitignore` automatically.

### Finding your API token

In the Voog admin panel: **Settings → Integrations → API** (or similar — the exact path varies by Voog version).

### Multiple sites

You can have multiple sections in `.voog` and switch between them with `--site`:

```ini
[staging.voog.com]
host=staging.voog.com
api_token=token_a

[production.voog.com]
host=production.voog.com
api_token=token_b
```

```bash
voog pull --site staging.voog.com
voog pull --site production.voog.com
```

---

## Directory structure

voog-cli creates/pulls files into this structure (same as the Ruby kit):

```
site-dir/
├── .voog                 ← config (not in git)
├── .gitignore
├── manifest.json         ← updated on every pull/push
├── layouts/              ← page layouts (.tpl)
├── components/           ← reusable components (.tpl)
├── stylesheets/          ← CSS files
├── javascripts/          ← JS files
├── images/               ← image assets
└── assets/               ← other assets (fonts, SVGs, etc.)
```

---

## Global options

| Flag | Description |
|---|---|
| `--verbose` / `-v` | Show API calls, file writes, and git operations |
| `--site NAME` | Use a named `.voog` section (multi-site) |
| `--version` | Print version and exit |

---

## Updating voog-cli

```bash
cd ~/path/to/voog-cli
git pull
```

---

## Migrating from the Ruby voog-kit

1. Keep your existing site directory as-is
2. Run `voog init --host your.voog.com --token YOUR_TOKEN` inside it
3. Run `voog pull` — all files are re-pulled reliably (including those with hyphens in filenames that the Ruby kit missed)
4. The Ruby kit is no longer needed

---

## Troubleshooting

**`No .voog config file found`**  
Run `voog init --host YOUR_HOST --token YOUR_TOKEN` in your site directory.

**`Authentication failed (401)`**  
Your API token in `.voog` is invalid or expired. Get a new one from the Voog admin panel.

**`HTTP 404`**  
The site hostname in `.voog` is wrong. Check the `host=` line.

**`CONFLICT — server was modified after last pull`**  
Someone edited the file on the server since your last `voog pull`. Run `voog pull` to sync, then re-apply your local changes.

**Files with hyphens not pulling with the Ruby kit**  
This is a known Ruby kit bug. Use `voog pull` instead — it calls the API directly.

**Git not found**  
Install git or add it to your PATH. The tool still works without git — you just won't get auto-commits or change detection for push.

---

## License

MIT
