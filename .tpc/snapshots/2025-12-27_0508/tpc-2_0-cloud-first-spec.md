# TPC 2.0: Cloud-First Architecture Spec

**Date:** December 24, 2025  
**Status:** Ready to Build  
**Goal:** Cloud folders for sync, GitHub for backup/import only

---

## The Problem (Why We're Doing This)

Current TPC treats GitHub as the sync mechanism between machines. This creates friction:

- Push/Pull discipline required (easy to forget)
- Commit messages required (another decision point)
- "Diverged histories" when you forget to pull
- Can't just *see* your files - GitHub is a black box
- Multiple steps to stay in sync
- TPC is finicky with Git edge cases

**The result:** Don doesn't trust TPC for the one thing it should do - keep his projects accessible across machines.

---

## The Solution: Cloud-First, GitHub-Optional

```
┌─────────────────┐
│  CLOUD FOLDER   │  ← Your projects live here (Dropbox/iCloud/OneDrive)
│                 │     Cloud service syncs between machines automatically
│  ProjectA/      │     This is the source of truth
│  ProjectB/      │
│  ProjectC/      │
└────────┬────────┘
         │
         │ (local git for version history - invisible to user)
         │
         ▼
┌─────────────────┐
│  GITHUB BACKUP  │  ← Optional offsite backup
│                 │     Clone once to import, push occasionally to backup
│                 │     One-way: local → GitHub
└─────────────────┘
```

**Git stays local** for version snapshots (time machine).  
**Cloud folder handles sync** between machines (invisible, not TPC's job).  
**GitHub is optional backup** - clone to import, push when you want.

---

## Two User Paths

### Path A: GitHub User (Has existing repos)

1. **Setup:** Log into GitHub in TPC Settings
2. **Import:** Clone projects down to cloud folder (one-time)
3. **Daily work:** Save Versions (local git commits)
4. **Sync:** Cloud folder handles it automatically
5. **Backup:** Push to GitHub when you feel like it
6. **Optional:** Weekly reminder "Hey, it's been a while since you backed up"

### Path B: Non-GitHub User (New to version control)

1. **Setup:** Point TPC at cloud folder, install git if needed
2. **Daily work:** Save Versions (local git commits)
3. **Sync:** Cloud folder handles it automatically
4. **Done.** No GitHub required, ever.

**Key insight:** Both paths converge on the same daily workflow. GitHub is just an onramp for existing projects and an offramp for backups.

---

## What Changes

| Current TPC | TPC 2.0 |
|-------------|---------|
| GitHub = sync layer | Cloud folder = sync layer |
| Push/Pull buttons prominent | Push hidden, Pull gone |
| "⬆ 3 to push" / "⬇ 2 to pull" | "✓ All saved" / "● Unsaved changes" |
| Two-way sync with GitHub | One-way backup to GitHub |
| "Connect to GitHub" required feel | GitHub entirely optional |
| Sync status = GitHub status | Sync status = local git status only |

## What Stays the Same

- Save Version (local git commit)
- Version History timeline
- Rollback to previous versions
- Pack (dependency scanning, venv, PyInstaller)
- Launch button
- Project Import/Adopt/New wizards
- Claude branch detection (still useful for Claude Code users)

---

## User Experience

### First Run

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   Where should TPC keep your projects?                  │
│                                                         │
│   We found these cloud folders on your system:          │
│                                                         │
│   ● iCloud Drive   ~/Library/Mobile Documents/.../      │
│   ○ Dropbox        ~/Dropbox/TPC Projects               │
│   ○ OneDrive       ~/OneDrive/TPC Projects              │
│                                                         │
│   ○ Local only     ~/Documents/TPC Projects             │
│     (won't sync between computers)                      │
│                                                         │
│   💡 Using a cloud folder means your projects           │
│      automatically appear on all your computers.        │
│                                                         │
│                    [ Let's Go ]                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Daily Workflow

**Status indicator (simplified):**
```
● Unsaved changes     →  You edited stuff since last Save Version
✓ All saved           →  Snapshot taken, you're good
```

No "3 to push." No "behind remote." Just: did you save or not?

**The GitHub section transforms:**

Current:
```
GitHub: ✓ In sync    [⬆ Push] [⬇ Pull]    
```

TPC 2.0:
```
Backup: Last backed up Dec 20    [Backup to GitHub]
        or
Backup: Not set up               [Set Up GitHub Backup]
        or
(nothing - if user never connected GitHub)
```

### Settings

```
┌─────────────────────────────────────────────────────────┐
│  Settings                                               │
│                                                         │
│  PROJECTS                                               │
│  ─────────────────────────────────────────────          │
│  Location: ~/iCloud Drive/TPC Projects   [Change]       │
│            ✓ Cloud folder detected (iCloud)             │
│                                                         │
│  GITHUB (Optional)                                      │
│  ─────────────────────────────────────────────          │
│  Status: Connected as @donburnsideAZ     [Disconnect]   │
│                                                         │
│  [Clone from GitHub]  ← Import existing repos           │
│                                                         │
│  ☐ Remind me to backup weekly                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### Phase 1: Cloud Folder Detection

**New module:** `core/cloud.py`

```python
def detect_cloud_folders() -> list[dict]:
    """
    Detect available cloud storage folders on this system.
    
    Returns list of dicts sorted by preference:
    {
        "service": "iCloud",
        "path": Path("~/Library/Mobile Documents/com~apple~CloudDocs/"),
        "display_path": "~/iCloud Drive/",
        "available": True
    }
    """
```

**Detection paths:**

| Service | Mac | Windows |
|---------|-----|---------|
| iCloud | `~/Library/Mobile Documents/com~apple~CloudDocs/` | `%USERPROFILE%\iCloudDrive\` |
| Dropbox | `~/Dropbox/` | `%USERPROFILE%\Dropbox\` |
| OneDrive | `~/Library/CloudStorage/OneDrive-Personal/` | `%OneDrive%` env var |
| Google Drive | `~/Library/CloudStorage/GoogleDrive-*/` | `%USERPROFILE%\Google Drive\` |

### Phase 2: First-Run Wizard

**New file:** `ui/wizards/first_run.py`

- Detect cloud folders
- Let user pick (or choose local)
- Create `TPC Projects` subfolder in chosen location
- Save to `~/.tpc/config.json`

**Config structure:**
```json
{
    "projects_root": "~/Library/Mobile Documents/com~apple~CloudDocs/TPC Projects",
    "cloud_service": "iCloud",
    "github_username": "donburnsideAZ",
    "backup_reminder": "weekly"
}
```

### Phase 3: Simplified Status UI

**Changes to `ui/workspace.py`:**

1. Remove Push/Pull buttons from main view
2. Change status to show local state only:
   - "✓ All saved" (no uncommitted changes)
   - "● Unsaved changes" (has uncommitted changes)
3. Replace "GitHub" section with simpler "Backup" section
4. Show last backup date, not sync status

**New status logic:**
```python
def get_simple_status(self) -> str:
    if self.project.has_unsaved_changes:
        return "● Unsaved changes"
    return "✓ All saved"
```

### Phase 4: GitHub as Backup Only

**Changes to GitHub integration:**

1. Remove Pull button entirely from normal workflow
2. "Push" becomes "Backup to GitHub" 
3. No sync status checking (no "ahead/behind")
4. Show "Last backed up: [date]" instead
5. Clone available from Settings for importing repos

**Backup flow:**
```python
def backup_to_github(self) -> tuple[bool, str]:
    """
    Push current state to GitHub as backup.
    
    Simple push - if it fails due to remote changes,
    tell the user and let them decide what to do.
    No force push, no automatic merging.
    """
    # Just a regular push
    # If remote has changes we don't have, that's unusual
    # (shouldn't happen in normal cloud-first workflow)
    # Show friendly error and suggest Clone if they need those changes
```

**Edge case - remote ahead of local:**

This shouldn't happen in normal workflow (cloud folder is source of truth). But if it does (user edited on github.com directly, or cloned on another machine without cloud folder):

```
┌─────────────────────────────────────────────────────────┐
│  GitHub has changes you don't have locally              │
│                                                         │
│  This can happen if you edited files directly on        │
│  GitHub, or worked on another computer without          │
│  your cloud folder.                                     │
│                                                         │
│  What would you like to do?                             │
│                                                         │
│  [Download GitHub version]  [Keep my version]  [Cancel] │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Phase 5: Clone Workflow

"Clone from GitHub" in Settings becomes the way to import existing repos:

1. User logs into GitHub in Settings
2. Clicks "Clone from GitHub"
3. Sees list of their repos (or pastes URL)
4. Clone goes to cloud folder location
5. Project appears in sidebar
6. Done - now it's a cloud-first project with GitHub as backup

---

## Migration Path

For existing TPC users:

1. **Existing projects keep working** - nothing breaks
2. **First run of TPC 2.0** shows location picker
3. **Can move projects** to cloud folder via Finder/Explorer
4. **TPC auto-discovers** projects in new location
5. **Old registry entries** cleaned up automatically

---

## File Changes Summary

| File | Changes |
|------|---------|
| `core/cloud.py` | **NEW** - Cloud folder detection |
| `core/project.py` | Add `last_backup_date`, remove sync status complexity |
| `ui/wizards/first_run.py` | **NEW** - First-run location picker |
| `ui/workspace.py` | Simplified status, backup section |
| `ui/settings_dialog.py` | Projects location, GitHub login, Clone button |
| `ui/main_window.py` | Trigger first-run wizard if no config |

---

## Backlog

| Priority | Item |
|----------|------|
| — | **Change detection on focus:** When TPC regains focus, check for unsaved changes and nudge user to Save Version. Natural workflow checkpoint without auto-commit noise. |
| — | Mac build cleanup: only output `.app` bundle, remove raw Unix executable |
| — | Windows icon conversion bug (P1 from Dec 16) |
| — | Subprocess cmd windows need `CREATE_NO_WINDOW` flag on Windows |
| — | Output console: Copy button |
| — | GitHub modals: Link to github.com (or user's repos if username stored) |

---

## Out of Scope (Intentionally)

- **Automatic background commits** - cloud sync churn makes this noisy; focus-based nudge is better
- **Automatic backup scheduling** - just reminders for now
- **Conflict detection for cloud sync** - cloud service's problem
- **Multi-user collaboration** - not the target audience
- **Branch management UI** - keep it simple
- **Two-way GitHub sync** - that's what current TPC does, and it's friction

### Future Bridge (If Needed)

If someone joins a team of Vibe Coders and needs GitHub to work like GitHub (real collaboration with branches, PRs, merge conflicts), that's a different tool or a future TPC Pro. We're not building for that now.

---

## Success Criteria

**Don can:**
1. ✅ Open TPC on Mac, see all projects
2. ✅ Walk to Windows machine, open TPC, see same projects with same history
3. ✅ Never think about Push/Pull for daily work
4. ✅ Hit "Backup to GitHub" occasionally for peace of mind
5. ✅ Trust that his files are where he can see them (in his cloud folder)

**TPC becomes:**
- A local time machine with a pretty face
- A "get my projects from GitHub" importer  
- A "backup my projects to GitHub" button
- NOT a Git client
- NOT a sync tool

---

## Build Order

1. **`core/cloud.py`** - Cloud folder detection (foundation)
2. **First-run wizard** - Location picker UI
3. **Settings update** - Projects location, GitHub section reorganized
4. **Workspace simplification** - New status indicators, backup button

Pack and Launch stay untouched - they already work great.

---

*"The best sync is the one you don't think about."*
