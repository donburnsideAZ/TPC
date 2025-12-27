"""
Workspace widgets for TPC.

The workspace is the main content area that changes based on context:
- WelcomeWidget: Shown when no project is selected
- WorkspaceWidget: Shown when working with a project
"""

import shutil
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QTextEdit,
    QLineEdit, QSizePolicy, QPlainTextEdit, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QProcess
from PyQt6.QtGui import QFont, QTextCursor

from core.project import Project


def get_python_executable() -> str:
    """
    Find the best Python executable to use for launching scripts.
    
    Priority:
    1. The Python running TPC (sys.executable) - if not frozen
    2. shutil.which("python3") - finds what terminal would use (Mac/Linux)
    3. shutil.which("python") - Windows fallback
    4. Platform default - last resort
    
    This ensures Launch uses the same Python as the user's terminal,
    not Apple's system Python at /usr/bin/python3 which has no packages.
    """
    # If TPC is running from source (not frozen .app), use the same Python
    if not getattr(sys, 'frozen', False):
        return sys.executable
    
    # For frozen apps, find Python in PATH (same as terminal would)
    # On Mac, prefer python3 but skip Apple's bare system Python
    if sys.platform != "win32":
        python_path = shutil.which("python3")
        if python_path and python_path != "/usr/bin/python3":
            return python_path
        # If only /usr/bin/python3 exists, still use it (better than nothing)
        if python_path:
            return python_path
    
    # Windows - try python first (more common), then python3
    python_path = shutil.which("python")
    if python_path:
        return python_path
    
    python_path = shutil.which("python3")
    if python_path:
        return python_path
    
    # Last resort - use platform default and hope for the best
    return "python" if sys.platform == "win32" else "python3"


# AI Support Prompt - copied to clipboard when user clicks the button
AI_SUPPORT_PROMPT = """I'm using an app called **TPC (Track Pack Click)** to manage my Python projects. TPC is designed for solo developers and makers who want version control and packaging without learning Git commands or terminal workflows.

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

- **Projects folder:** Cloud folder like `~/Dropbox/TPC Projects/` (configurable)
- **Project config:** `ProjectFolder/.tpc/project.json`
- **Global config:** `~/.tpc/config.json`
- **Build virtual environments:** `~/.tpc/venvs/ProjectName/`
- **Build output:** `ProjectFolder/TPC Builds/`
- **GitHub credentials:** Stored in system keyring (never in files)

### What NOT to Suggest

Please don't tell me to:
- Open terminal/command prompt
- Type `git` commands
- Run `pip` or `pyinstaller` directly
- Edit `.git/` folder contents
- Use `--force` flags manually

TPC exists specifically so I don't have to do these things.

### My Current Issue

"""


class WelcomeWidget(QWidget):
    """
    Welcome screen shown when no project is selected.
    
    The first impression - friendly, inviting, not intimidating.
    """
    
    new_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)
        
        # Center content vertically
        layout.addStretch(1)
        
        # Main message
        title = QLabel("Ready to ship something?")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel(
            "Pick a project from the sidebar, or start fresh."
        )
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(40)
        
        # Action buttons (centered)
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(16)
        
        btn_layout.addStretch()
        
        btn_new = QPushButton("Start New Project")
        btn_new.setObjectName("welcomeButtonPrimary")
        btn_new.clicked.connect(self.new_clicked.emit)
        btn_layout.addWidget(btn_new)
        
        btn_layout.addStretch()
        
        layout.addWidget(btn_container)
        
        layout.addStretch(2)
        
        hint = QLabel(
            "Tip: Use Import to bring an existing project folder into TPC."
        )
        hint.setObjectName("welcomeHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        
        layout.addStretch(1)
        
        self.apply_styles()
    
    def apply_styles(self):
        self.setStyleSheet("""
            WelcomeWidget {
                background-color: #ffffff;
            }
            
            #welcomeTitle {
                color: #000000;
                font-size: 28px;
                font-weight: 600;
            }
            
            #welcomeSubtitle {
                color: #666666;
                font-size: 16px;
                margin-top: 8px;
            }
            
            #welcomeButtonPrimary {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 500;
            }
            
            #welcomeButtonPrimary:hover {
                background-color: #5aafff;
            }
            
            #welcomeButtonPrimary:pressed {
                background-color: #3a8eef;
            }
            
            #welcomeButtonSecondary {
                background-color: #f1f1f1;
                color: #333333;
                border: 1px solid #e0e0e0;
                padding: 14px 28px;
                border-radius: 8px;
                font-size: 15px;
            }
            
            #welcomeButtonSecondary:hover {
                background-color: #e4e4e4;
                color: #000000;
            }
            
            #welcomeHint {
                color: #888888;
                font-size: 13px;
            }
        """)


class WorkspaceWidget(QWidget):
    """
    Project workspace - shown when a project is selected.
    
    Contains:
    - Project header with name and status
    - Big action buttons (Launch, Save Version)
    - Output panel for script results
    - Version timeline
    """
    
    project_changed = pyqtSignal()  # Emitted when project state changes
    
    def __init__(self):
        super().__init__()
        self.project: Project | None = None
        # Track running processes PER PROJECT (keyed by project path string)
        self.running_processes: dict[str, QProcess] = {}
        # Track output per project so switching back shows previous output
        self.project_outputs: dict[str, str] = {}
        self.setup_ui()
    
    def _get_project_key(self) -> str | None:
        """Get the current project's unique key (path as string)."""
        if not self.project:
            return None
        return str(self.project.path)
    
    def _is_current_project_running(self) -> bool:
        """Check if the currently displayed project has a running process."""
        key = self._get_project_key()
        if not key:
            return False
        process = self.running_processes.get(key)
        return process is not None and process.state() == QProcess.ProcessState.Running
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)
        
        # === HEADER (full width) ===
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Project info (left side)
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        self.project_name = QLabel("No Project Selected")
        self.project_name.setObjectName("projectName")
        info_layout.addWidget(self.project_name)
        
        self.project_path = QLabel("")
        self.project_path.setObjectName("projectPath")
        info_layout.addWidget(self.project_path)
        
        header_layout.addWidget(info)
        header_layout.addStretch()
        
        # Sync with GitHub button (fetches remote, shows branches if any)
        self.btn_sync = QPushButton("Sync with GitHub")
        self.btn_sync.setObjectName("btnSync")
        self.btn_sync.setToolTip("Check GitHub for branches and updates")
        self.btn_sync.clicked.connect(self.on_sync_github)
        header_layout.addWidget(self.btn_sync)
        
        main_layout.addWidget(header)
        
        # === BRANCH WARNING (hidden by default) ===
        self.branch_warning = QWidget()
        self.branch_warning.setObjectName("branchWarning")
        branch_warning_layout = QHBoxLayout(self.branch_warning)
        branch_warning_layout.setContentsMargins(16, 12, 16, 12)
        branch_warning_layout.setSpacing(12)
        
        warning_icon = QLabel("!")
        warning_icon.setObjectName("warningIcon")
        branch_warning_layout.addWidget(warning_icon)
        
        self.branch_warning_text = QLabel("")
        self.branch_warning_text.setObjectName("branchWarningText")
        self.branch_warning_text.setWordWrap(True)
        branch_warning_layout.addWidget(self.branch_warning_text, 1)
        
        self.btn_switch_branch = QPushButton("Switch to main")
        self.btn_switch_branch.setObjectName("btnSwitchBranch")
        self.btn_switch_branch.clicked.connect(self.on_switch_to_main)
        branch_warning_layout.addWidget(self.btn_switch_branch)
        
        self.branch_warning.hide()  # Hidden by default
        main_layout.addWidget(self.branch_warning)
        
        # === GIT MISSING WARNING (hidden by default) ===
        self.git_missing_warning = QWidget()
        self.git_missing_warning.setObjectName("gitMissingWarning")
        git_warning_layout = QHBoxLayout(self.git_missing_warning)
        git_warning_layout.setContentsMargins(16, 12, 16, 12)
        git_warning_layout.setSpacing(12)
        
        git_warning_icon = QLabel("!")
        git_warning_icon.setObjectName("warningIcon")
        git_warning_layout.addWidget(git_warning_icon)
        
        git_warning_text = QLabel(
            "Version tracking was lost (the .git folder is missing). "
            "Click Restore to start tracking again from your current files."
        )
        git_warning_text.setObjectName("gitMissingText")
        git_warning_text.setWordWrap(True)
        git_warning_layout.addWidget(git_warning_text, 1)
        
        self.btn_restore_git = QPushButton("Restore Tracking")
        self.btn_restore_git.setObjectName("btnRestoreGit")
        self.btn_restore_git.clicked.connect(self.on_restore_git)
        git_warning_layout.addWidget(self.btn_restore_git)
        
        self.git_missing_warning.hide()  # Hidden by default
        main_layout.addWidget(self.git_missing_warning)
        
        # === CLAUDE BRANCHES WARNING (hidden by default) ===
        self.claude_branches_warning = QWidget()
        self.claude_branches_warning.setObjectName("claudeBranchesWarning")
        claude_warning_layout = QVBoxLayout(self.claude_branches_warning)
        claude_warning_layout.setContentsMargins(16, 12, 16, 12)
        claude_warning_layout.setSpacing(8)
        
        # Header row
        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        branch_icon = QLabel("🔀")
        branch_icon.setObjectName("branchIcon")
        header_layout.addWidget(branch_icon)
        
        self.branch_header = QLabel("Remote branches with changes")
        self.branch_header.setObjectName("claudeBranchesHeader")
        header_layout.addWidget(self.branch_header)
        header_layout.addStretch()
        
        claude_warning_layout.addWidget(header_row)
        
        # Branch info (will be populated dynamically)
        self.remote_branch_info = QLabel("")
        self.remote_branch_info.setObjectName("claudeBranchInfo")
        self.remote_branch_info.setWordWrap(True)
        claude_warning_layout.addWidget(self.remote_branch_info)
        
        # Buttons row
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(12)
        
        self.btn_merge_branch = QPushButton("Merge into main")
        self.btn_merge_branch.setObjectName("btnMergeClaude")
        self.btn_merge_branch.clicked.connect(self.on_merge_remote_branch)
        btn_row_layout.addWidget(self.btn_merge_branch)
        
        self.btn_ignore_branch = QPushButton("Ignore")
        self.btn_ignore_branch.setObjectName("btnIgnoreClaude")
        self.btn_ignore_branch.clicked.connect(self.on_ignore_remote_branch)
        btn_row_layout.addWidget(self.btn_ignore_branch)
        
        btn_row_layout.addStretch()
        claude_warning_layout.addWidget(btn_row)
        
        self.claude_branches_warning.hide()  # Hidden by default
        self._current_remote_branch = None  # The branch we're offering to merge
        main_layout.addWidget(self.claude_branches_warning)
        
        # === TWO COLUMN LAYOUT ===
        columns = QSplitter(Qt.Orientation.Horizontal)
        columns.setChildrenCollapsible(False)
        
        # === LEFT COLUMN ===
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 12, 0)
        left_layout.setSpacing(16)
        
        # Action buttons
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)
        
        self.btn_launch = QPushButton("▶  Launch")
        self.btn_launch.setObjectName("actionButtonPrimary")
        self.btn_launch.clicked.connect(self.on_launch)
        actions_layout.addWidget(self.btn_launch)
        
        self.btn_save = QPushButton("+  Save Version")
        self.btn_save.setObjectName("actionButtonSecondary")
        self.btn_save.clicked.connect(self.on_save_version)
        actions_layout.addWidget(self.btn_save)
        
        actions_layout.addStretch()
        left_layout.addWidget(actions)
        
        # === BACKUP SECTION (simplified from GitHub) ===
        backup_section = QWidget()
        backup_layout = QHBoxLayout(backup_section)
        backup_layout.setContentsMargins(0, 0, 0, 0)
        backup_layout.setSpacing(12)
        
        # Backup label
        backup_label = QLabel("Backup:")
        backup_label.setObjectName("backupLabel")
        backup_layout.addWidget(backup_label)
        
        # Backup status (last backup date or "Not set up")
        self.backup_status = QLabel("Not set up")
        self.backup_status.setObjectName("backupStatus")
        backup_layout.addWidget(self.backup_status)
        
        backup_layout.addSpacing(8)
        
        # Backup Now button (replaces Push)
        self.btn_backup = QPushButton("Backup Now")
        self.btn_backup.setObjectName("backupButton")
        self.btn_backup.clicked.connect(self.on_backup)
        self.btn_backup.setEnabled(False)
        backup_layout.addWidget(self.btn_backup)
        
        # Connect to GitHub link (hidden when already connected)
        self.btn_setup_backup = QPushButton("Connect to GitHub")
        self.btn_setup_backup.setObjectName("backupSetupLink")
        self.btn_setup_backup.clicked.connect(self.on_connect_github)
        backup_layout.addWidget(self.btn_setup_backup)
        
        # Get from GitHub link (hidden by default, for when you need to pull)
        self.btn_get_from_github = QPushButton("Get from GitHub")
        self.btn_get_from_github.setObjectName("backupGetLink")
        self.btn_get_from_github.clicked.connect(self.on_pull)
        self.btn_get_from_github.hide()
        backup_layout.addWidget(self.btn_get_from_github)
        
        backup_layout.addStretch()
        left_layout.addWidget(backup_section)
        
        # === OUTPUT PANEL ===
        output_header_row = QWidget()
        output_header_layout = QHBoxLayout(output_header_row)
        output_header_layout.setContentsMargins(0, 0, 0, 0)
        
        output_header = QLabel("OUTPUT")
        output_header.setObjectName("sectionHeader")
        output_header_layout.addWidget(output_header)
        
        output_header_layout.addStretch()
        
        self.btn_copy_output = QPushButton("Copy")
        self.btn_copy_output.setObjectName("btnSmall")
        self.btn_copy_output.clicked.connect(self.copy_output)
        output_header_layout.addWidget(self.btn_copy_output)
        
        self.btn_clear_output = QPushButton("Clear")
        self.btn_clear_output.setObjectName("btnSmall")
        self.btn_clear_output.clicked.connect(self.clear_output)
        output_header_layout.addWidget(self.btn_clear_output)
        
        left_layout.addWidget(output_header_row)
        
        self.output_panel = QPlainTextEdit()
        self.output_panel.setObjectName("outputPanel")
        self.output_panel.setReadOnly(True)
        self.output_panel.setPlaceholderText("Click Launch to run your script...")
        
        # Use monospace font for output
        output_font = QFont("Monaco", 11)
        output_font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_panel.setFont(output_font)
        
        left_layout.addWidget(self.output_panel, 1)
        
        columns.addWidget(left_column)
        
        # === RIGHT COLUMN ===
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(8)
        
        # === ACTION BUTTONS (top) ===
        self.btn_copy_ai_prompt = QPushButton("📋 Copy AI Support Prompt")
        self.btn_copy_ai_prompt.setObjectName("btnRightColumn")
        self.btn_copy_ai_prompt.setToolTip("Copy a prompt to paste into ChatGPT, Claude, etc. when you need help")
        self.btn_copy_ai_prompt.clicked.connect(self.on_copy_ai_prompt)
        right_layout.addWidget(self.btn_copy_ai_prompt)
        
        self.btn_open_build_folder = QPushButton("📂 Open Build Folder")
        self.btn_open_build_folder.setObjectName("btnRightColumn")
        self.btn_open_build_folder.clicked.connect(self.on_open_build_folder)
        right_layout.addWidget(self.btn_open_build_folder)
        
        right_layout.addSpacing(8)
        
        # === VERSION HISTORY ===
        timeline_header = QLabel("VERSION HISTORY")
        timeline_header.setObjectName("sectionHeader")
        right_layout.addWidget(timeline_header)
        
        self.timeline = QScrollArea()
        self.timeline.setObjectName("timeline")
        self.timeline.setWidgetResizable(True)
        self.timeline.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.timeline_content = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_content)
        self.timeline_layout.setContentsMargins(8, 8, 8, 8)
        self.timeline_layout.setSpacing(4)
        self.timeline_layout.addStretch()
        
        self.timeline.setWidget(self.timeline_content)
        right_layout.addWidget(self.timeline, 1)
        
        columns.addWidget(right_column)
        
        # Set column proportions (60% left, 40% right)
        columns.setSizes([550, 350])
        
        main_layout.addWidget(columns, 1)
        
        self.apply_styles()
    
    def set_project(self, project: Project):
        """Load a project into the workspace."""
        # Save current project's output before switching
        old_key = self._get_project_key()
        if old_key:
            self.project_outputs[old_key] = self.output_panel.toPlainText()
        
        self.project = project
        
        # Restore this project's output (or clear if none)
        new_key = self._get_project_key()
        if new_key and new_key in self.project_outputs:
            self.output_panel.setPlainText(self.project_outputs[new_key])
        else:
            self.output_panel.clear()
        
        self.refresh_ui()
    
    def refresh_ui(self, fetch_github: bool = False):
        """Update all UI elements to reflect current project state.
        
        Args:
            fetch_github: If True, fetch remote status (slow). If False, show basic status.
        """
        if not self.project:
            return
        
        # Update header
        self.project_name.setText(self.project.name)
        self.project_path.setText(str(self.project.path))
        
        # Update Launch button based on THIS project's running state
        if self._is_current_project_running():
            self.btn_launch.setEnabled(False)
            self.btn_launch.setText("⏳ Running...")
        else:
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("▶  Launch")
        
        # Check for missing git (highest priority warning)
        self.refresh_git_warning()
        
        # Check for branch issues
        self.refresh_branch_warning()
        
        # Update backup status (only fetch if requested)
        self.refresh_backup_status(fetch_remote=fetch_github)
        
        # Check for unmerged branches (only when syncing)
        if fetch_github:
            self.refresh_remote_branches()
        
        # Update timeline
        self.refresh_timeline()
    
    def refresh_timeline(self):
        """Rebuild the version timeline."""
        # Clear existing items (except the stretch at the end)
        while self.timeline_layout.count() > 1:
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.project:
            return
        
        history = self.project.get_version_history()
        
        if not history:
            empty = QLabel("No versions yet. Click 'Save Version' to save your first snapshot.")
            empty.setObjectName("timelineEmpty")
            empty.setWordWrap(True)
            self.timeline_layout.insertWidget(0, empty)
            return
        
        for i, version in enumerate(history):
            item = VersionItem(
                message=version["message"],
                date=version["date"],
                hash=version["hash"],
                is_latest=(i == 0)
            )
            # Connect restore signal
            item.restore_requested.connect(self.on_restore_version)
            self.timeline_layout.insertWidget(self.timeline_layout.count() - 1, item)
    
    def on_restore_version(self, commit_hash: str, message: str):
        """Handle request to restore to a previous version."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Restore to Previous Version?",
            f"This will restore your files to:\n\n\"{message}\"\n\n"
            "Your current files will be replaced, but nothing is deleted - "
            "a new version will be created and you can always restore forward again.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Do the restore
        success, result_message = self.project.restore_to_version(commit_hash, message)
        
        if success:
            QMessageBox.information(self, "Restored!", result_message)
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Restore Failed", result_message)
    
    def refresh_git_warning(self):
        """Check if git is missing and show warning if so."""
        if not self.project:
            self.git_missing_warning.hide()
            return
        
        if self.project.has_git:
            self.git_missing_warning.hide()
        else:
            self.git_missing_warning.show()
    
    def on_restore_git(self):
        """Handle restoring git tracking for a project."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Disable button during operation
        self.btn_restore_git.setEnabled(False)
        self.btn_restore_git.setText("Restoring...")
        
        success, message = self.project.reinitialize_git()
        
        # Re-enable button
        self.btn_restore_git.setText("Restore Tracking")
        self.btn_restore_git.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Tracking Restored!", message)
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Restore Failed", message)
    
    def refresh_branch_warning(self):
        """Check if we're on a non-main branch and show warning if so."""
        if not self.project:
            self.branch_warning.hide()
            return
        
        current_branch = self.project.get_current_branch()
        
        if current_branch is None:
            # No git repo
            self.branch_warning.hide()
            return
        
        if self.project.is_on_main_branch():
            self.branch_warning.hide()
        else:
            main_name = self.project.get_main_branch_name()
            self.branch_warning_text.setText(
                f"You're on branch '{current_branch}' instead of '{main_name}'. "
                f"This can happen when Claude creates a separate branch. "
                f"Switch back to keep your work in one place."
            )
            self.btn_switch_branch.setText(f"Switch to {main_name}")
            self.branch_warning.show()
    
    def refresh_remote_branches(self):
        """Check for any unmerged branches on the remote (not just claude/*)."""
        if not self.project:
            self.claude_branches_warning.hide()
            return
        
        if not self.project.has_remote():
            self.claude_branches_warning.hide()
            return
        
        # Only check if we're on main
        if not self.project.is_on_main_branch():
            self.claude_branches_warning.hide()
            return
        
        # Get ALL unmerged remote branches (not just claude/*)
        unmerged = self.project.get_unmerged_remote_branches()
        
        # Filter out handled branches (unless they have new commits)
        unmerged = [b for b in unmerged if not self.project.is_branch_handled(b["branch"])[0]]
        
        if not unmerged:
            self.claude_branches_warning.hide()
            return
        
        # Show the most recent unmerged branch
        latest = unmerged[0]
        self._current_remote_branch = latest["branch"]
        
        commits_text = "1 commit" if latest["commits_ahead"] == 1 else f"{latest['commits_ahead']} commits"
        
        self.remote_branch_info.setText(
            f"<b>{latest['display_name']}</b> — {latest['date']}<br>"
            f"<i>\"{latest['message']}\"</i><br>"
            f"<span style='color: #666;'>{commits_text} not in main</span>"
        )
        
        if len(unmerged) > 1:
            self.remote_branch_info.setText(
                self.remote_branch_info.text() + 
                f"<br><span style='color: #888;'>+ {len(unmerged) - 1} more branch{'es' if len(unmerged) > 2 else ''}</span>"
            )
        
        self.claude_branches_warning.show()
    
    def on_merge_remote_branch(self):
        """Merge the selected remote branch into main."""
        if not self.project or not self._current_remote_branch:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Disable buttons during operation
        self.btn_merge_branch.setEnabled(False)
        self.btn_merge_branch.setText("Merging...")
        
        success, message = self.project.merge_branch(self._current_remote_branch)
        
        # Re-enable buttons
        self.btn_merge_branch.setText("Merge into main")
        self.btn_merge_branch.setEnabled(True)
        
        if success:
            # Mark this branch as handled in project config
            self.project.mark_branch_handled(self._current_remote_branch, "merged")
            
            QMessageBox.information(
                self,
                "Merged!",
                f"{message}\n\n"
                "The branch changes are now in your main branch."
            )
            self._current_remote_branch = None
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Merge Failed", message)
    
    def on_ignore_remote_branch(self):
        """Ignore the current remote branch suggestion."""
        if self._current_remote_branch and self.project:
            # Mark this branch as handled in project config
            self.project.mark_branch_handled(self._current_remote_branch, "ignored")
            
            self._current_remote_branch = None
            self.refresh_remote_branches()
    
    def on_sync_github(self):
        """Sync with GitHub - fetch and check for branches."""
        if not self.project:
            return
        
        # Check if GitHub is connected
        if not self.project.has_remote():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Not Connected",
                "This project isn't connected to GitHub yet.\n\n"
                "Click 'Connect to GitHub' to set it up."
            )
            return
        
        # Show we're syncing
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("Syncing...")
        
        # Force a refresh including GitHub fetch
        self.refresh_ui(fetch_github=True)
        
        # Restore button
        self.btn_sync.setText("Sync with GitHub")
        self.btn_sync.setEnabled(True)
    
    def on_switch_to_main(self):
        """Handle switching back to main branch."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Check for unsaved changes first
        if self.project.has_unsaved_changes:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Would you like to save a version before switching branches?\n\n"
                "If you don't save, your changes will be stashed (hidden) and can be recovered later.",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Save:
                # Save version first
                from PyQt6.QtWidgets import QInputDialog
                message, ok = QInputDialog.getText(
                    self,
                    "Save Version",
                    "What changed? (optional)",
                    text=""
                )
                if ok:
                    from datetime import datetime
                    if not message.strip():
                        message = f"Saved before switching branches at {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
                    saved, status = self.project.save_version(message.strip())
                    if not saved and status == "needs_identity":
                        # Show identity dialog
                        if self._show_identity_dialog():
                            self.project.save_version(message.strip())
                else:
                    return  # They cancelled the save dialog
        
        # Now switch
        main_name = self.project.get_main_branch_name()
        success, message = self.project.switch_to_main(force=True)
        
        if success:
            QMessageBox.information(
                self,
                "Switched!",
                f"You're now on '{main_name}'.\n\n"
                "Your work is all in one place again."
            )
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(
                self,
                "Couldn't Switch",
                f"{message}\n\n"
                "You might need to resolve this manually, or ask Claude for help."
            )
    
    def on_launch(self):
        """Launch the project's main file."""
        if not self.project:
            return
        
        project_key = self._get_project_key()
        if not project_key:
            return
        
        # Check if main file exists
        main_file_path = self.project.path / self.project.main_file
        if not main_file_path.exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Main File Not Found",
                f"The main file '{self.project.main_file}' doesn't exist.\n\n"
                f"Expected: {main_file_path}\n\n"
                "You may need to update the project settings."
            )
            return
        
        # Clear previous output for this project
        self.output_panel.clear()
        
        # Find the right Python executable
        python_exe = get_python_executable()
        self.append_output(f"▶ Running {self.project.main_file}...\n")
        self.append_output(f"  Using: {python_exe}\n\n")
        
        # Disable launch button while running
        self.btn_launch.setEnabled(False)
        self.btn_launch.setText("⏳ Running...")
        
        # Use QProcess for better Qt integration
        process = QProcess(self)
        process.setWorkingDirectory(str(self.project.path))
        
        # Clean environment to avoid PyInstaller conflicts
        # When TPC runs as a bundled app, it sets env vars that pollute child processes
        from PyQt6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        
        # Remove PyInstaller and Qt-specific variables that cause library conflicts
        # When TPC runs as a bundled app, these vars point to TPC's Qt libraries
        # which conflict with the child process's own PyQt6 installation
        cleanup_vars = [
            # PyInstaller runtime variables
            '_MEIPASS', '_MEIPASS2', '_PYI_ARCHIVE_FILE', '_PYI_SPLASH_IPC',
            # Library path overrides (can cause wrong libraries to load)
            'LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH',
            # Python path (child should use its own environment)
            'PYTHONPATH',
            # Tcl/Tk paths (for tkinter apps)
            'TCL_LIBRARY', 'TK_LIBRARY',
            # Qt plugin and framework paths - THE CRITICAL ONES for this bug
            # These cause "Class X is implemented in both..." errors on macOS
            'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
            'QML_IMPORT_PATH', 'QML2_IMPORT_PATH',
            'QT_DEBUG_PLUGINS', 'QT_QPA_PLATFORM',
            # Qt for Python / PySide paths
            'PYSIDE_DESIGNER_PLUGINS',
        ]
        for var in cleanup_vars:
            if env.contains(var):
                env.remove(var)
        
        process.setProcessEnvironment(env)
        
        # Store which project this process belongs to
        process.setProperty("project_key", project_key)
        
        # Connect signals
        process.readyReadStandardOutput.connect(lambda: self.on_stdout_ready(process))
        process.readyReadStandardError.connect(lambda: self.on_stderr_ready(process))
        process.finished.connect(lambda exit_code, exit_status: self.on_process_finished(process, exit_code, exit_status))
        
        # Track this process for this project
        self.running_processes[project_key] = process
        
        # Start the process with the correct Python
        process.start(python_exe, [self.project.main_file])
    
    def on_stdout_ready(self, process: QProcess):
        """Handle stdout data from the running process."""
        project_key = process.property("project_key")
        data = process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        
        # Only append to output panel if this is the currently viewed project
        if project_key == self._get_project_key():
            self.append_output(text)
        else:
            # Store in project outputs for later display
            if project_key in self.project_outputs:
                self.project_outputs[project_key] += text
            else:
                self.project_outputs[project_key] = text
    
    def on_stderr_ready(self, process: QProcess):
        """Handle stderr data from the running process."""
        project_key = process.property("project_key")
        data = process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        
        # Only append to output panel if this is the currently viewed project
        if project_key == self._get_project_key():
            self.append_output(text, is_error=True)
        else:
            # Store in project outputs for later display
            if project_key in self.project_outputs:
                self.project_outputs[project_key] += text
            else:
                self.project_outputs[project_key] = text
    
    def on_process_finished(self, process: QProcess, exit_code: int, exit_status):
        """Handle process completion."""
        project_key = process.property("project_key")
        
        # Build completion message
        if exit_code == 0:
            completion_msg = f"\n✓ Finished successfully"
        else:
            completion_msg = f"\n✗ Exited with code {exit_code}"
        
        # If this is the currently viewed project, update UI directly
        if project_key == self._get_project_key():
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("▶  Launch")
            self.append_output(completion_msg)
        else:
            # Store completion message in project outputs
            if project_key in self.project_outputs:
                self.project_outputs[project_key] += completion_msg
            else:
                self.project_outputs[project_key] = completion_msg
        
        # Remove from running processes
        if project_key in self.running_processes:
            del self.running_processes[project_key]
    
    def append_output(self, text: str, is_error: bool = False):
        """Append text to the output panel."""
        cursor = self.output_panel.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_panel.setTextCursor(cursor)
        self.output_panel.insertPlainText(text)
        
        # Auto-scroll to bottom
        scrollbar = self.output_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_output(self):
        """Clear the output panel."""
        self.output_panel.clear()
        # Also clear stored output for current project
        key = self._get_project_key()
        if key and key in self.project_outputs:
            del self.project_outputs[key]
    
    def copy_output(self):
        """Copy output panel contents to clipboard."""
        from PyQt6.QtWidgets import QApplication
        text = self.output_panel.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
    
    def on_open_build_folder(self):
        """Open the TPC Builds folder for this project."""
        if not self.project:
            return
        
        import subprocess
        import platform
        from core import subprocess_args
        
        builds_folder = self.project.path / "TPC Builds"
        
        # Create if it doesn't exist
        builds_folder.mkdir(parents=True, exist_ok=True)
        
        path = str(builds_folder)
        
        if platform.system() == "Darwin":
            subprocess.run(["open", path])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", path], **subprocess_args())
        else:
            subprocess.run(["xdg-open", path])
    
    def on_copy_ai_prompt(self):
        """Copy the AI support prompt to clipboard."""
        from PyQt6.QtWidgets import QApplication, QToolTip
        from PyQt6.QtCore import QPoint
        
        clipboard = QApplication.clipboard()
        clipboard.setText(AI_SUPPORT_PROMPT)
        
        # Show brief confirmation near the button
        QToolTip.showText(
            self.btn_copy_ai_prompt.mapToGlobal(QPoint(0, -30)),
            "✓ Copied! Paste into ChatGPT, Claude, etc.",
            self.btn_copy_ai_prompt,
            msecShowTime=2000
        )
    
    def on_save_version(self):
        """Save the current state as a new version."""
        if not self.project:
            return
        
        # Check if there are changes first
        if not self.project.has_unsaved_changes:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Nothing to Save",
                "No changes detected since your last save.\n\n"
                "Keep working - I'll be here when you're ready."
            )
            return
        
        # Prompt for a commit message
        from PyQt6.QtWidgets import QInputDialog
        message, ok = QInputDialog.getText(
            self,
            "Save Version",
            "What changed? (optional)",
            text=""
        )
        
        if not ok:
            return  # User cancelled
        
        # Use provided message or generate default
        if not message.strip():
            from datetime import datetime
            message = f"Saved at {datetime.now().strftime('%Y-%m-%d %I:%M %p')}"
        
        saved, status = self.project.save_version(message.strip())
        
        if saved:
            self.refresh_ui()
            self.project_changed.emit()
        elif status == "needs_identity":
            # Git needs user identity configured - show friendly dialog
            if self._show_identity_dialog():
                # Try again after configuring identity
                saved, status = self.project.save_version(message.strip())
                if saved:
                    self.refresh_ui()
                    self.project_changed.emit()
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Save Failed", f"Could not save version: {status}")
        elif status == "nothing_to_save":
            pass  # Already handled above, but just in case
        elif status.startswith("error:"):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Save Failed", f"Could not save version:\n\n{status[7:]}")
    
    def _show_identity_dialog(self) -> bool:
        """
        Show dialog to configure git identity.
        
        Returns True if identity was configured, False if cancelled.
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("One Quick Thing...")
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        header = QLabel("What name should appear in your version history?")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: #333;")
        header.setWordWrap(True)
        layout.addWidget(header)
        
        explanation = QLabel(
            "TPC tracks who made each version. This only needs to be set once."
        )
        explanation.setStyleSheet("color: #666; font-size: 13px;")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        layout.addSpacing(8)
        
        # Name input
        name_label = QLabel("Name:")
        name_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #555;")
        layout.addWidget(name_label)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Your Name")
        name_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """)
        layout.addWidget(name_input)
        
        # Email input
        email_label = QLabel("Email:")
        email_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #555;")
        layout.addWidget(email_label)
        
        email_input = QLineEdit()
        email_input.setPlaceholderText("you@example.com")
        email_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """)
        layout.addWidget(email_input)
        
        layout.addSpacing(8)
        
        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: 1px solid #ccc;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        btn_cancel.clicked.connect(dialog.reject)
        btn_row.addWidget(btn_cancel)
        
        btn_save = QPushButton("Save")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5aafff;
            }
        """)
        btn_save.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_save)
        
        layout.addLayout(btn_row)
        
        # Focus the name field
        name_input.setFocus()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            email = email_input.text().strip()
            
            if name and email:
                success, _ = self.project.configure_git_identity(name, email)
                return success
            elif name:
                # Email is optional, use a placeholder
                success, _ = self.project.configure_git_identity(name, f"{name.lower().replace(' ', '.')}@tpc.local")
                return success
        
        return False
    
    def refresh_backup_status(self, fetch_remote: bool = False):
        """Update the backup status display.
        
        TPC 2.0: Cloud folders handle sync. GitHub is just backup.
        Show last backup date, not sync status.
        """
        if not self.project:
            self.backup_status.setText("No project")
            self.btn_backup.setEnabled(False)
            self.btn_setup_backup.show()
            self.btn_get_from_github.hide()
            return
        
        if not self.project.has_remote():
            self.backup_status.setText("Not set up")
            self.backup_status.setStyleSheet("color: #888888;")
            self.btn_backup.setEnabled(False)
            self.btn_setup_backup.show()
            self.btn_get_from_github.hide()
            return
        
        # We have a remote - show backup status
        self.btn_setup_backup.hide()
        self.btn_backup.setEnabled(True)
        
        # Get last push date from git
        last_backup = self.project.get_last_push_date()
        
        if last_backup:
            self.backup_status.setText(f"Last: {last_backup}")
            self.backup_status.setStyleSheet("color: #666666;")
        else:
            self.backup_status.setText("Never backed up")
            self.backup_status.setStyleSheet("color: #f39c12;")
        
        # Only show "Get from GitHub" if there are remote changes
        # But only check if explicitly requested (slow operation)
        if fetch_remote:
            status = self.project.get_sync_status()
            if status.get("behind", 0) > 0:
                self.btn_get_from_github.show()
            else:
                self.btn_get_from_github.hide()
        else:
            self.btn_get_from_github.hide()
    
    def on_backup(self):
        """Backup to GitHub - one-way push for safety."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox, QApplication
        
        # Disable button during operation
        self.btn_backup.setEnabled(False)
        self.btn_backup.setText("Backing up...")
        
        # Force UI update
        QApplication.processEvents()
        
        # Do the push
        success, message = self.project.push_to_github()
        
        # Re-enable button
        self.btn_backup.setText("Backup Now")
        self.btn_backup.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Backed Up!", "Your project is safely backed up to GitHub.")
            self.refresh_backup_status()
        elif message == "DIVERGED":
            # Show conflict resolution dialog
            self.show_diverged_dialog()
        else:
            QMessageBox.warning(self, "Backup Failed", message)
    
    def on_push(self):
        """Legacy push method - redirects to on_backup."""
        self.on_backup()
    
    def show_diverged_dialog(self):
        """Show dialog for resolving diverged histories."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Histories Have Diverged")
        dialog.setModal(True)
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Explanation
        header = QLabel("Your local and GitHub have different histories")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: #333;")
        layout.addWidget(header)
        
        explanation = QLabel(
            "This usually happens when:\n"
            "• Another tool (like Claude Code) made commits on GitHub\n"
            "• You worked on this project from another computer\n"
            "• Something got out of sync\n\n"
            "Which version is correct?"
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(explanation)
        
        layout.addSpacing(8)
        
        # Option 1: Use local (force push)
        local_btn = QPushButton("Use my local version")
        local_btn.setToolTip("Overwrites GitHub with your local files")
        local_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #5aafff;
            }
        """)
        local_btn.clicked.connect(lambda: self.resolve_diverged(dialog, "local"))
        layout.addWidget(local_btn)
        
        local_hint = QLabel("GitHub will be overwritten with what you have here")
        local_hint.setStyleSheet("color: #888; font-size: 12px; margin-left: 8px;")
        layout.addWidget(local_hint)
        
        layout.addSpacing(4)
        
        # Option 2: Use remote (reset to GitHub)
        remote_btn = QPushButton("Use GitHub's version")
        remote_btn.setToolTip("Overwrites your local files with what's on GitHub")
        remote_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        remote_btn.clicked.connect(lambda: self.resolve_diverged(dialog, "remote"))
        layout.addWidget(remote_btn)
        
        remote_hint = QLabel("Your local files will be replaced with GitHub's version")
        remote_hint.setStyleSheet("color: #888; font-size: 12px; margin-left: 8px;")
        layout.addWidget(remote_hint)
        
        layout.addSpacing(12)
        
        # Cancel
        cancel_btn = QPushButton("Cancel - I'll figure this out later")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: 1px solid #ccc;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        
        dialog.exec()
    
    def resolve_diverged(self, dialog, choice: str):
        """Handle the user's choice for diverged histories."""
        from PyQt6.QtWidgets import QMessageBox, QApplication
        
        dialog.accept()
        
        if choice == "local":
            # Force push (use local version as backup)
            self.btn_backup.setEnabled(False)
            self.btn_backup.setText("Overwriting backup...")
            QApplication.processEvents()
            
            success, message = self.project.force_push_to_github()
            
            self.btn_backup.setText("Backup Now")
            self.btn_backup.setEnabled(True)
            
            if success:
                QMessageBox.information(self, "Done!", "Your local version is now backed up to GitHub.")
                self.refresh_backup_status()
            else:
                QMessageBox.warning(self, "Backup Failed", message)
                
        elif choice == "remote":
            # Confirm this destructive action
            reply = QMessageBox.warning(
                self,
                "Are you sure?",
                "This will replace ALL your local files with GitHub's version.\n\n"
                "Any local changes will be lost.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            self.btn_backup.setEnabled(False)
            self.btn_backup.setText("Getting from GitHub...")
            QApplication.processEvents()
            
            success, message = self.project.reset_to_remote()
            
            self.btn_backup.setText("Backup Now")
            self.btn_backup.setEnabled(True)
            
            if success:
                QMessageBox.information(self, "Done!", "Your files have been replaced with GitHub's version.")
                self.refresh_ui()
                self.project_changed.emit()
            else:
                QMessageBox.warning(self, "Reset Failed", message)
    
    def on_pull(self):
        """Get latest from GitHub (pull)."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox, QApplication
        
        # Disable buttons during operation
        self.btn_backup.setEnabled(False)
        self.btn_get_from_github.setEnabled(False)
        self.btn_get_from_github.setText("Getting...")
        QApplication.processEvents()
        
        # Do the pull
        success, message = self.project.pull_from_github()
        
        # Re-enable buttons
        self.btn_get_from_github.setText("Get from GitHub")
        self.btn_backup.setEnabled(True)
        self.btn_get_from_github.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Got Latest!", message)
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Pull Failed", message)
    
    def on_connect_github(self):
        """Show dialog to set up GitHub backup with repo dropdown."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
            QHBoxLayout, QMessageBox, QComboBox, QWidget, QApplication
        )
        from PyQt6.QtCore import QThread, pyqtSignal
        from core.github import has_github_credentials, get_github_username, fetch_user_repos
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Connect to GitHub")
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Check if connected to GitHub
        if not has_github_credentials():
            # Not connected - show message to go to settings
            message = QLabel(
                "You'll need to connect to GitHub first.\n\n"
                "Go to Settings → GitHub to sign in with your Personal Access Token."
            )
            message.setStyleSheet("color: #666666; font-size: 14px;")
            message.setWordWrap(True)
            layout.addWidget(message)
            
            layout.addSpacing(16)
            
            btn_settings = QPushButton("Open Settings")
            btn_settings.setStyleSheet("""
                QPushButton {
                    background-color: #4a9eff;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #5aafff;
                }
            """)
            btn_settings.clicked.connect(lambda: self._open_settings_from_dialog(dialog))
            layout.addWidget(btn_settings)
            
            layout.addStretch()
            
            btn_cancel = QPushButton("Cancel")
            btn_cancel.clicked.connect(dialog.reject)
            layout.addWidget(btn_cancel)
            
            dialog.exec()
            return
        
        # Connected - show repo picker
        username = get_github_username()
        
        header = QLabel(f"Connect {self.project.name} to GitHub")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #333;")
        layout.addWidget(header)
        
        subheader = QLabel(f"Signed in as {username}")
        subheader.setStyleSheet("color: #888888; font-size: 13px;")
        layout.addWidget(subheader)
        
        layout.addSpacing(8)
        
        instructions = QLabel(
            "Select an existing repository or enter a URL.\n"
            "Your project will back up to this repo when you click 'Backup Now'."
        )
        instructions.setStyleSheet("color: #666666; font-size: 13px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Repo dropdown
        repo_label = QLabel("Repository")
        repo_label.setStyleSheet("color: #555555; font-size: 14px; font-weight: 500;")
        layout.addWidget(repo_label)
        
        self._backup_repo_combo = QComboBox()
        self._backup_repo_combo.setMinimumHeight(40)
        self._backup_repo_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 8px 12px;
                color: #333333;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #4a9eff;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                selection-background-color: #e8f4fd;
                selection-color: #333333;
            }
        """)
        self._backup_repo_combo.addItem("Loading repositories...")
        self._backup_repo_combo.setEnabled(False)
        self._backup_repo_combo.currentIndexChanged.connect(
            lambda: self._on_backup_repo_selected(dialog)
        )
        layout.addWidget(self._backup_repo_combo)
        
        # Manual URL toggle
        self._backup_manual_visible = False
        btn_manual = QPushButton("Or enter a URL manually...")
        btn_manual.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                padding: 4px 0;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                color: #3a8eef;
                text-decoration: underline;
            }
        """)
        btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_manual)
        
        # Manual URL input (hidden by default)
        self._backup_manual_widget = QWidget()
        manual_layout = QVBoxLayout(self._backup_manual_widget)
        manual_layout.setContentsMargins(0, 8, 0, 0)
        manual_layout.setSpacing(8)
        
        self._backup_url_input = QLineEdit()
        self._backup_url_input.setPlaceholderText("https://github.com/username/repository")
        self._backup_url_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                font-size: 14px;
                border: 1px solid #cccccc;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """)
        manual_layout.addWidget(self._backup_url_input)
        
        self._backup_manual_widget.hide()
        layout.addWidget(self._backup_manual_widget)
        
        def toggle_manual():
            self._backup_manual_visible = not self._backup_manual_visible
            if self._backup_manual_visible:
                self._backup_manual_widget.show()
                self._backup_repo_combo.setEnabled(False)
                btn_manual.setText("Use dropdown instead...")
            else:
                self._backup_manual_widget.hide()
                self._backup_repo_combo.setEnabled(True)
                btn_manual.setText("Or enter a URL manually...")
        
        btn_manual.clicked.connect(toggle_manual)
        
        # Pre-fill if we have a saved URL
        if self.project.github_repo:
            self._backup_url_input.setText(self.project.github_repo)
        
        layout.addStretch()
        
        # Status label
        self._backup_status = QLabel("")
        self._backup_status.setStyleSheet("font-size: 13px;")
        layout.addWidget(self._backup_status)
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 10px 24px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
        """)
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        
        self._backup_connect_btn = QPushButton("Connect")
        self._backup_connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5aafff;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        self._backup_connect_btn.setEnabled(False)
        self._backup_connect_btn.clicked.connect(lambda: self._do_connect_github(dialog))
        btn_layout.addWidget(self._backup_connect_btn)
        
        layout.addWidget(btn_row)
        
        # Store repos list and dialog reference
        self._backup_repos = []
        self._backup_dialog = dialog
        
        # Fetch repos in background
        class RepoFetchWorker(QThread):
            finished = pyqtSignal(bool, str, list)
            
            def run(self):
                success, message, repos = fetch_user_repos()
                self.finished.emit(success, message, repos)
        
        def on_repos_loaded(success, message, repos):
            if success:
                self._backup_repos = repos
                self._backup_repo_combo.clear()
                self._backup_repo_combo.addItem("— Select a repository —", "")
                
                for repo in repos:
                    display = repo['full_name']
                    if repo.get('private'):
                        display += " 🔒"
                    self._backup_repo_combo.addItem(display, repo['clone_url'])
                
                self._backup_repo_combo.setEnabled(True)
            else:
                self._backup_repo_combo.clear()
                self._backup_repo_combo.addItem(f"Error: {message}", "")
                # Enable manual entry if fetch failed
                toggle_manual()
        
        self._backup_fetch_worker = RepoFetchWorker()
        self._backup_fetch_worker.finished.connect(on_repos_loaded)
        self._backup_fetch_worker.start()
        
        dialog.exec()
    
    def _on_backup_repo_selected(self, dialog):
        """Handle repo selection from dropdown."""
        if not hasattr(self, '_backup_repo_combo'):
            return
        
        url = self._backup_repo_combo.currentData()
        if url:
            self._backup_connect_btn.setEnabled(True)
        else:
            self._backup_connect_btn.setEnabled(False)
    
    def _open_settings_from_dialog(self, dialog):
        """Open settings and close the current dialog."""
        dialog.reject()
        from ui.settings_dialog import SettingsDialog
        settings = SettingsDialog(self)
        settings.exec()
    
    def _do_connect_github(self, dialog):
        """Actually connect to GitHub after dialog input."""
        from PyQt6.QtWidgets import QMessageBox
        
        # Get URL from dropdown or manual input
        if hasattr(self, '_backup_manual_visible') and self._backup_manual_visible:
            url = self._backup_url_input.text().strip()
        else:
            url = self._backup_repo_combo.currentData()
            if not url:
                url = ""
        
        if not url:
            QMessageBox.warning(dialog, "No Repository Selected", "Please select a repository or enter a URL.")
            return
        
        # Basic URL validation for manual entry
        if not (url.startswith("https://github.com/") or url.startswith("git@github.com:")):
            QMessageBox.warning(
                dialog, 
                "Invalid URL", 
                "That doesn't look like a GitHub URL.\n\n"
                "It should start with https://github.com/ or git@github.com:"
            )
            return
        
        # Try to set the remote
        success, message = self.project.set_remote(url)
        
        if success:
            dialog.accept()
            self.refresh_backup_status()
            QMessageBox.information(
                self,
                "Connected!",
                f"Your project is now connected to GitHub.\n\n"
                f"Click 'Backup Now' anytime to push a copy to GitHub."
            )
        else:
            QMessageBox.warning(dialog, "Connection Failed", message)
    
    def _open_github_link(self, url: str):
        """Open a GitHub URL in the default browser."""
        import webbrowser
        webbrowser.open(url)
    
    def apply_styles(self):
        self.setStyleSheet("""
            WorkspaceWidget {
                background-color: #ffffff;
            }
            
            #projectName {
                color: #000000;
                font-size: 22px;
                font-weight: 600;
            }
            
            #projectPath {
                color: #666666;
                font-size: 12px;
            }
            
            #warningIcon {
                font-size: 14px;
                font-weight: bold;
                color: #856404;
                background-color: #ffc107;
                border-radius: 10px;
                min-width: 20px;
                max-width: 20px;
                min-height: 20px;
                max-height: 20px;
                text-align: center;
            }
            
            #claudeBranchIcon {
                font-size: 13px;
                font-weight: 600;
                color: #1a5a9e;
            }
            
            #btnSync {
                background-color: #f1f1f1;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #btnSync:hover {
                background-color: #e4e4e4;
                border-color: #999999;
            }
            
            #btnSync:pressed {
                background-color: #d4d4d4;
            }
            
            #btnSync:disabled {
                background-color: #f8f8f8;
                color: #aaaaaa;
                border-color: #dddddd;
            }
            
            #branchWarning {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 8px;
            }
            
            #branchWarningText {
                color: #856404;
                font-size: 13px;
            }
            
            #btnSwitchBranch {
                background-color: #ffc107;
                color: #856404;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            #btnSwitchBranch:hover {
                background-color: #e0a800;
            }
            
            #btnSwitchBranch:pressed {
                background-color: #d39e00;
            }
            
            #gitMissingWarning {
                background-color: #fdecea;
                border: 1px solid #e74c3c;
                border-radius: 8px;
            }
            
            #gitMissingText {
                color: #922820;
                font-size: 13px;
            }
            
            #btnRestoreGit {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            #btnRestoreGit:hover {
                background-color: #c0392b;
            }
            
            #btnRestoreGit:pressed {
                background-color: #a93226;
            }
            
            #claudeBranchesWarning {
                background-color: #e8f4fd;
                border: 1px solid #4a9eff;
                border-radius: 8px;
            }
            
            #claudeBranchesHeader {
                color: #1a5a9e;
                font-size: 14px;
                font-weight: 600;
                margin-left: 8px;
            }
            
            #claudeBranchInfo {
                color: #333333;
                font-size: 13px;
                margin-left: 28px;
            }
            
            #btnMergeClaude {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            
            #btnMergeClaude:hover {
                background-color: #5aafff;
            }
            
            #btnMergeClaude:pressed {
                background-color: #3a8eef;
            }
            
            #btnIgnoreClaude {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #btnIgnoreClaude:hover {
                background-color: #f0f0f0;
            }
            
            #actionButtonPrimary {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 16px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                min-width: 140px;
            }
            
            #actionButtonPrimary:hover {
                background-color: #3ddc81;
            }
            
            #actionButtonPrimary:pressed {
                background-color: #27ae60;
            }
            
            #actionButtonPrimary:disabled {
                background-color: #95a5a6;
            }
            
            #actionButtonSecondary {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 16px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                min-width: 140px;
            }
            
            #actionButtonSecondary:hover {
                background-color: #5aafff;
            }
            
            #actionButtonSecondary:pressed {
                background-color: #3a8eef;
            }
            
            #backupLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
            }
            
            #backupStatus {
                font-size: 13px;
                font-weight: 500;
            }
            
            #backupButton {
                background-color: #f1f1f1;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #backupButton:hover {
                background-color: #e4e4e4;
                border-color: #999999;
            }
            
            #backupButton:pressed {
                background-color: #d4d4d4;
            }
            
            #backupButton:disabled {
                background-color: #f8f8f8;
                color: #aaaaaa;
                border-color: #dddddd;
            }
            
            #backupSetupLink {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                padding: 8px 16px;
                font-size: 13px;
                text-decoration: underline;
            }
            
            #backupSetupLink:hover {
                color: #3a8eef;
            }
            
            #backupGetLink {
                background-color: transparent;
                color: #666666;
                border: none;
                padding: 8px 12px;
                font-size: 12px;
            }
            
            #backupGetLink:hover {
                color: #333333;
                text-decoration: underline;
            }
            
            #sectionHeader {
                color: #666666;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            #btnSmall {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            
            #btnSmall:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            #outputPanel {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }
            
            #timeline {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            
            #btnRightColumn {
                background-color: #f1f1f1;
                color: #333333;
                border: 1px solid #e0e0e0;
                padding: 12px 16px;
                border-radius: 6px;
                font-size: 13px;
                text-align: left;
            }
            
            #btnRightColumn:hover {
                background-color: #e4e4e4;
                border-color: #cccccc;
            }
            
            #timelineEmpty {
                color: #666666;
                font-size: 13px;
                padding: 20px;
            }
        """)


class VersionItem(QFrame):
    """A single version in the timeline."""
    
    # Signal emitted when user wants to restore to this version
    restore_requested = pyqtSignal(str, str)  # hash, message
    
    def __init__(self, message: str, date: str, hash: str, is_latest: bool = False):
        super().__init__()
        self.hash = hash
        self.message = message
        self.is_latest = is_latest
        
        self.setObjectName("versionItem")
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Indicator dot
        dot = QLabel("●" if is_latest else "○")
        dot.setObjectName("versionDot")
        layout.addWidget(dot)
        
        # Message and date
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(4)
        
        msg_label = QLabel(message)
        msg_label.setObjectName("versionMessage")
        msg_label.setWordWrap(True)
        info_layout.addWidget(msg_label)
        
        # Format date nicely
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date.replace(" ", "T").split("+")[0])
            nice_date = dt.strftime("%b %d, %Y at %I:%M %p")
        except:
            nice_date = date
        
        date_label = QLabel(nice_date)
        date_label.setObjectName("versionDate")
        info_layout.addWidget(date_label)
        
        layout.addWidget(info, 1)
        
        # Short hash
        hash_label = QLabel(hash[:7])
        hash_label.setObjectName("versionHash")
        layout.addWidget(hash_label)
        
        # Apply styles based on whether this is the latest version
        if is_latest:
            self.setStyleSheet("""
                #versionItem {
                    background-color: transparent;
                    border-radius: 8px;
                }
                
                #versionDot {
                    font-size: 12px;
                    color: #4a9eff;
                    min-width: 20px;
                }
                
                #versionMessage {
                    color: #000000;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                #versionDate {
                    color: #666666;
                    font-size: 12px;
                }
                
                #versionHash {
                    color: #888888;
                    font-size: 11px;
                    font-family: monospace;
                }
            """)
        else:
            self.setStyleSheet("""
                #versionItem {
                    background-color: transparent;
                    border-radius: 8px;
                }
                
                #versionItem:hover {
                    background-color: #eeeeee;
                }
                
                #versionDot {
                    font-size: 12px;
                    color: #aaaaaa;
                    min-width: 20px;
                }
                
                #versionMessage {
                    color: #888888;
                    font-size: 14px;
                }
                
                #versionDate {
                    color: #888888;
                    font-size: 12px;
                }
                
                #versionHash {
                    color: #888888;
                    font-size: 11px;
                    font-family: monospace;
                }
            """)
    
    def show_context_menu(self, position):
        """Show context menu for this version."""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                color: #333333;
            }
            QMenu::item:selected {
                background-color: #e8e8e8;
                color: #000000;
            }
        """)
        
        if self.is_latest:
            # Can't restore to current version
            action = menu.addAction("This is the current version")
            action.setEnabled(False)
        else:
            restore_action = menu.addAction("Restore to this version")
            restore_action.triggered.connect(
                lambda: self.restore_requested.emit(self.hash, self.message)
            )
        
        menu.exec(self.mapToGlobal(position))