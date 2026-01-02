# Session Recap - December 29, 2025

## TPC v3.3.0: Security + Folder Projects + Secrets Detection 🔒📂🔍

Three major updates in this session:

---

## 1. Security Fix: Keychain Storage for GitHub PAT

**The Problem:** GitHub Personal Access Tokens were stored in plaintext JSON at `~/.tpc/config.json`.

**The Fix:** Migrated to secure system keychain storage via the `keyring` Python library.

### Key Features
- **Automatic Migration**: Existing plaintext tokens moved to keychain on first run
- **Cross-Platform**: macOS Keychain, Windows Credential Manager, Linux Secret Service
- **Graceful Fallback**: If keyring unavailable, falls back to config file with warning
- **Settings shows security status**: "🔒 Token stored securely in system keychain"

---

## 2. Non-Python Project Support (Folder Projects)

**The Problem:** TPC was Python-only. Users wanted to track other project types.

**The Fix:** Added "folder" project type that:
- Opens in Finder/Explorer instead of running Python
- Hides main file selection in import wizard
- Still gets full snapshot versioning and GitHub backup

### UI Changes
- **Import Wizard**: Radio buttons to select project type
- **Workspace**: Launch button shows "📂 Open Folder" for folder projects
- **Auto-detection**: If no .py files found, defaults to folder project

---

## 3. Secrets Detection Before GitHub Backup

**The Problem:** Users might accidentally push API keys, passwords, or private keys to GitHub.

**The Fix:** Scans for sensitive files before first GitHub backup.

### What It Detects

**High Risk 🔴:**
- `.env`, `.env.local`, `.env.production`
- `credentials.json`, `secrets.json`
- `*.pem`, `*.key`, SSH keys (`id_rsa`, etc.)
- AWS credentials, `.netrc`

**Medium Risk 🟡:**
- `.env.development`, `.env.staging`
- Files with `secret`, `token`, `password`, `credential` in name
- `.npmrc`, `.pypirc`

**Low Risk 🟢:**
- `config.json`, `settings.json`
- Database files (`.sqlite`, `.db`)
- Backup files (`.bak`)

### User Options
When secrets are found, dialog offers:
1. **Cancel Backup** - Stop and review
2. **Add to Ignore List** - Exclude files from backup permanently
3. **Backup Anyway** - User takes responsibility

### When It Runs
- Only on FIRST backup (when `last_backup` is None)
- Respects existing ignore patterns
- Skips `.tpc/`, `.git/`, `node_modules/`, etc.

---

## UI Polish

- Label: "Backup:" → "GitHub Backup:"
- Button: "Set Up Backup" → "Set Up GitHub"
- Added "Create a new repository on GitHub →" link in setup dialog

---

## Files Created/Modified

| File | Changes |
|------|---------|
| `core/secrets.py` | **NEW** - Secrets detection module |
| `core/__init__.py` | Export secrets functions, version 3.3.0 |
| `core/project_v3.py` | Added project_type, launch_command fields |
| `ui/workspace_v3.py` | SecretsWarningDialog, GitHub label updates, folder project handling |
| `ui/wizards/import_project.py` | Project type radio buttons |
| `core/github.py` | Keychain storage |
| `ui/settings_dialog.py` | Security status indicator |

---

## Testing

### Test Secrets Detection
1. Create a project with a `.env` file
2. Set up GitHub backup
3. Click "Backup Now"
4. Should see warning dialog with the .env file listed
5. Choose "Add to Ignore List"
6. File added to project's ignore_patterns

### Test Folder Projects
1. Import any non-Python folder
2. Launch button should show "📂 Open Folder"
3. Clicking opens in Finder/Explorer

---

## Backlog Status

| Item | Status |
|------|--------|
| Security: GitHub PAT in keychain | ✅ Done |
| Non-Python project support | ✅ Done |
| Secrets detection before backup | ✅ Done |
| Mac build cleanup (.app only) | Pending |
| Friendly error parsing | Pending |

---

*"TPC: Protecting you from yourself since 2025."*

🔒📂🔍 Ship it!

