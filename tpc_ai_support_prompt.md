# TPC AI Support Prompt

**Copy and paste this into your AI assistant when you need help with TPC.**

---

## Prompt Start

I'm using an app called **TPC (Track Pack Click)** to manage my Python projects. TPC is designed for solo developers and makers who want version control and packaging without learning Git commands or terminal workflows.

**Please help me within TPC's mental model — don't suggest terminal commands or Git CLI operations.** TPC handles Git invisibly behind a friendly GUI.

### What TPC Does

**Track** (version control):
- "Save Version" = Creates a snapshot of your project (git commit under the hood)
- Version History = Visual timeline showing all your saved versions
- TPC auto-detects and offers to merge Claude/AI branches

**Sync** (cloud-first in TPC 2.0):
- Projects live in a cloud folder (iCloud, Dropbox, OneDrive, etc.)
- Sync between computers happens automatically via the cloud service
- GitHub is optional backup, not required for sync

**Backup** (GitHub integration):
- "Backup Now" = One-way push to GitHub for safety
- "Set Up Backup" = Connect a project to a GitHub repo
- "Get from GitHub" = Pull changes (only shown when needed)

**Pack** (build distributable apps):
- Scans Python imports automatically
- Creates isolated virtual environment
- Converts PNG icons to platform-specific formats
- Builds standalone .exe (Windows) or .app (Mac) using PyInstaller

### TPC 2.0 Mental Model

```
Your Files ←→ Cloud Folder ←→ Other Computers
                  ↓
              GitHub (backup)
```

- Cloud folder = automatic sync (not TPC's job)
- Save Version = local snapshots (time machine)
- Backup Now = safety copy to GitHub (occasional)

### TPC Vocabulary → Git Translation

| TPC Says | Git Equivalent |
|----------|----------------|
| Save Version | `git add -A && git commit` |
| Backup Now | `git push` |
| Get from GitHub | `git pull` |
| Version History | `git log` |
| "Unsaved changes" | Uncommitted changes |
| "Last: Dec 24" | Date of last push to remote |

### Where Things Live

- **Projects folder:** Cloud folder like `~/Dropbox/TPC Projects/` (configurable on first run)
- **Project config:** `ProjectFolder/.tpc/project.json`
- **Global config:** `~/.tpc/config.json`
- **Build virtual environments:** `~/.tpc/venvs/ProjectName/`
- **Build output:** `ProjectFolder/TPC Builds/`
- **GitHub credentials:** Stored in system keyring (never in files)

### Common Issues & TPC Solutions

**"Histories have diverged"**
- TPC shows a dialog with two buttons: "Use my local version" or "Use GitHub's version"
- Pick whichever is correct — TPC handles the rest

**"You're on branch X instead of main"**
- Yellow warning banner appears in TPC
- Click "Switch to main" button
- This happens when Claude Code or another AI tool created a branch

**"Claude made changes on a separate branch"**
- Blue banner shows unmerged AI branches
- Click "Merge into main" to incorporate changes
- Or "Ignore" to dismiss

**"What name should appear in your version history?"**
- TPC needs your name/email for version tracking (one-time setup)
- Just fill in the dialog and continue

**Build fails with missing module**
- Check if the package is in requirements.txt
- TPC scans imports but can't detect dynamic imports
- Add missing packages to requirements.txt manually

**"Main file not found"**
- Edit `.tpc/project.json` and fix the `main_file` value
- Or re-import the project with correct entry point

**App launches from TPC but crashes (Mac)**
- Known issue: Launching PyQt apps from bundled TPC.app can cause Qt library conflicts
- Workaround: Launch built apps directly from Finder or TPC Builds folder
- Apps work fine when launched standalone

### What NOT to Suggest

Please don't tell me to:
- Open terminal/command prompt
- Type `git` commands
- Run `pip` or `pyinstaller` directly
- Edit `.git/` folder contents
- Use `--force` flags manually

TPC exists specifically so I don't have to do these things. If TPC can't handle something through its GUI, let me know and I'll request the feature.

### About My Setup

- **TPC Version:** 2.0.0
- **Platforms:** Windows and Mac
- **My projects are in:** A cloud folder (configured on first run)

### My Current Issue

[Describe your problem here]

---

## Prompt End
