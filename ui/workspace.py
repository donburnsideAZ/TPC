"""
Workspace widgets for PTC.

The workspace is the main content area that changes based on context:
- WelcomeWidget: Shown when no project is selected
- WorkspaceWidget: Shown when working with a project
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QTextEdit,
    QLineEdit, QSizePolicy, QPlainTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QProcess
from PyQt6.QtGui import QFont, QTextCursor

from core.project import Project


class WelcomeWidget(QWidget):
    """
    Welcome screen shown when no project is selected.
    
    The first impression - friendly, inviting, not intimidating.
    """
    
    new_clicked = pyqtSignal()
    adopt_clicked = pyqtSignal()
    
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
        
        btn_adopt = QPushButton("Adopt Existing Script")
        btn_adopt.setObjectName("welcomeButtonSecondary")
        btn_adopt.clicked.connect(self.adopt_clicked.emit)
        btn_layout.addWidget(btn_adopt)
        
        btn_layout.addStretch()
        
        layout.addWidget(btn_container)
        
        # Fun hint at the bottom
        layout.addStretch(2)
        
        hint = QLabel(
            "💡 Got a script in Downloads? The Adopt button is your friend."
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
        self.current_process: QProcess | None = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        
        # === HEADER ===
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
        
        # Refresh button
        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setObjectName("btnRefresh")
        self.btn_refresh.setToolTip("Refresh - check for remote changes")
        self.btn_refresh.clicked.connect(self.on_refresh)
        header_layout.addWidget(self.btn_refresh)
        
        # Status indicator (right side)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        header_layout.addWidget(self.status_label)
        
        layout.addWidget(header)
        
        # === BRANCH WARNING (hidden by default) ===
        self.branch_warning = QWidget()
        self.branch_warning.setObjectName("branchWarning")
        branch_warning_layout = QHBoxLayout(self.branch_warning)
        branch_warning_layout.setContentsMargins(16, 12, 16, 12)
        branch_warning_layout.setSpacing(12)
        
        warning_icon = QLabel("⚠️")
        warning_icon.setStyleSheet("font-size: 16px;")
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
        layout.addWidget(self.branch_warning)
        
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
        
        claude_icon = QLabel("🔀")
        claude_icon.setStyleSheet("font-size: 16px;")
        header_layout.addWidget(claude_icon)
        
        claude_header = QLabel("Claude made changes on a separate branch")
        claude_header.setObjectName("claudeBranchesHeader")
        header_layout.addWidget(claude_header)
        header_layout.addStretch()
        
        claude_warning_layout.addWidget(header_row)
        
        # Branch info (will be populated dynamically)
        self.claude_branch_info = QLabel("")
        self.claude_branch_info.setObjectName("claudeBranchInfo")
        self.claude_branch_info.setWordWrap(True)
        claude_warning_layout.addWidget(self.claude_branch_info)
        
        # Buttons row
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(12)
        
        self.btn_merge_claude = QPushButton("Merge into main")
        self.btn_merge_claude.setObjectName("btnMergeClaude")
        self.btn_merge_claude.clicked.connect(self.on_merge_claude_branch)
        btn_row_layout.addWidget(self.btn_merge_claude)
        
        self.btn_ignore_claude = QPushButton("Ignore")
        self.btn_ignore_claude.setObjectName("btnIgnoreClaude")
        self.btn_ignore_claude.clicked.connect(self.on_ignore_claude_branches)
        btn_row_layout.addWidget(self.btn_ignore_claude)
        
        btn_row_layout.addStretch()
        claude_warning_layout.addWidget(btn_row)
        
        self.claude_branches_warning.hide()  # Hidden by default
        self._ignored_claude_branches = set()  # Track ignored branches
        self._current_claude_branch = None  # The branch we're offering to merge
        layout.addWidget(self.claude_branches_warning)
        
        # === BIG ACTION BUTTONS ===
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(16)
        
        self.btn_launch = QPushButton("▶  Launch")
        self.btn_launch.setObjectName("actionButtonPrimary")
        self.btn_launch.clicked.connect(self.on_launch)
        actions_layout.addWidget(self.btn_launch)
        
        self.btn_save = QPushButton("💾  Save Version")
        self.btn_save.setObjectName("actionButtonSecondary")
        self.btn_save.clicked.connect(self.on_save_version)
        actions_layout.addWidget(self.btn_save)
        
        actions_layout.addStretch()
        
        layout.addWidget(actions)
        
        # === GITHUB SECTION ===
        github_section = QWidget()
        github_layout = QHBoxLayout(github_section)
        github_layout.setContentsMargins(0, 0, 0, 0)
        github_layout.setSpacing(12)
        
        # GitHub icon/label
        github_label = QLabel("GitHub:")
        github_label.setObjectName("githubLabel")
        github_layout.addWidget(github_label)
        
        # Sync status indicator
        self.sync_status = QLabel("Not connected")
        self.sync_status.setObjectName("syncStatus")
        github_layout.addWidget(self.sync_status)
        
        github_layout.addSpacing(8)
        
        # Push button
        self.btn_push = QPushButton("⬆ Push")
        self.btn_push.setObjectName("githubButton")
        self.btn_push.clicked.connect(self.on_push)
        self.btn_push.setEnabled(False)
        github_layout.addWidget(self.btn_push)
        
        # Pull button  
        self.btn_pull = QPushButton("⬇ Pull")
        self.btn_pull.setObjectName("githubButton")
        self.btn_pull.clicked.connect(self.on_pull)
        self.btn_pull.setEnabled(False)
        github_layout.addWidget(self.btn_pull)
        
        github_layout.addSpacing(8)
        
        # Connect button (shown when not connected)
        self.btn_connect = QPushButton("Connect to GitHub")
        self.btn_connect.setObjectName("githubConnectButton")
        self.btn_connect.clicked.connect(self.on_connect_github)
        github_layout.addWidget(self.btn_connect)
        
        github_layout.addStretch()
        
        layout.addWidget(github_section)
        
        # === OUTPUT PANEL ===
        output_header_row = QWidget()
        output_header_layout = QHBoxLayout(output_header_row)
        output_header_layout.setContentsMargins(0, 0, 0, 0)
        
        output_header = QLabel("Output")
        output_header.setObjectName("sectionHeader")
        output_header_layout.addWidget(output_header)
        
        output_header_layout.addStretch()
        
        self.btn_clear_output = QPushButton("Clear")
        self.btn_clear_output.setObjectName("btnSmall")
        self.btn_clear_output.clicked.connect(self.clear_output)
        output_header_layout.addWidget(self.btn_clear_output)
        
        layout.addWidget(output_header_row)
        
        self.output_panel = QPlainTextEdit()
        self.output_panel.setObjectName("outputPanel")
        self.output_panel.setReadOnly(True)
        self.output_panel.setMinimumHeight(120)
        self.output_panel.setMaximumHeight(180)
        self.output_panel.setPlaceholderText("Click Launch to run your script...")
        
        # Use monospace font for output
        output_font = QFont("Monaco", 12)
        output_font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_panel.setFont(output_font)
        
        layout.addWidget(self.output_panel)
        
        # === VERSION TIMELINE ===
        timeline_header = QLabel("Version History")
        timeline_header.setObjectName("sectionHeader")
        layout.addWidget(timeline_header)
        
        self.timeline = QScrollArea()
        self.timeline.setObjectName("timeline")
        self.timeline.setWidgetResizable(True)
        self.timeline.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.timeline_content = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_content)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(8)
        self.timeline_layout.addStretch()
        
        self.timeline.setWidget(self.timeline_content)
        layout.addWidget(self.timeline, 1)
        
        self.apply_styles()
    
    def set_project(self, project: Project):
        """Load a project into the workspace."""
        self.project = project
        self.clear_output()
        self.refresh_ui()
    
    def refresh_ui(self):
        """Update all UI elements to reflect current project state."""
        if not self.project:
            return
        
        # Update header
        self.project_name.setText(self.project.name)
        self.project_path.setText(str(self.project.path))
        
        # Update status
        if self.project.has_unsaved_changes:
            self.status_label.setText("● Unsaved changes")
            self.status_label.setStyleSheet("color: #ffa500;")
        else:
            self.status_label.setText("✓ All saved")
            self.status_label.setStyleSheet("color: #4a9eff;")
        
        # Check for branch issues
        self.refresh_branch_warning()
        
        # Update GitHub status
        self.refresh_github_status()
        
        # Check for unmerged Claude branches
        self.refresh_claude_branches()
        
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
            self.timeline_layout.insertWidget(self.timeline_layout.count() - 1, item)
    
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
    
    def refresh_claude_branches(self):
        """Check for unmerged Claude branches on the remote."""
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
        
        # Get unmerged Claude branches
        unmerged = self.project.get_unmerged_claude_branches()
        
        # Filter out ignored branches
        unmerged = [b for b in unmerged if b["branch"] not in self._ignored_claude_branches]
        
        if not unmerged:
            self.claude_branches_warning.hide()
            return
        
        # Show the most recent unmerged branch
        latest = unmerged[0]
        self._current_claude_branch = latest["branch"]
        
        commits_text = "1 commit" if latest["commits_ahead"] == 1 else f"{latest['commits_ahead']} commits"
        
        self.claude_branch_info.setText(
            f"<b>{latest['display_name']}</b> — {latest['date']}<br>"
            f"<i>\"{latest['message']}\"</i><br>"
            f"<span style='color: #666;'>{commits_text} not in main</span>"
        )
        
        if len(unmerged) > 1:
            self.claude_branch_info.setText(
                self.claude_branch_info.text() + 
                f"<br><span style='color: #888;'>+ {len(unmerged) - 1} more branch{'es' if len(unmerged) > 2 else ''}</span>"
            )
        
        self.claude_branches_warning.show()
    
    def on_merge_claude_branch(self):
        """Merge the suggested Claude branch into main."""
        if not self.project or not self._current_claude_branch:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Disable buttons during operation
        self.btn_merge_claude.setEnabled(False)
        self.btn_merge_claude.setText("Merging...")
        
        success, message = self.project.merge_branch(self._current_claude_branch)
        
        # Re-enable buttons
        self.btn_merge_claude.setText("Merge into main")
        self.btn_merge_claude.setEnabled(True)
        
        if success:
            QMessageBox.information(
                self,
                "Merged!",
                f"{message}\n\n"
                "The Claude branch changes are now in your main branch.\n"
                "Don't forget to Push to update GitHub."
            )
            self._current_claude_branch = None
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Merge Failed", message)
    
    def on_ignore_claude_branches(self):
        """Ignore the current Claude branch suggestion."""
        if self._current_claude_branch:
            self._ignored_claude_branches.add(self._current_claude_branch)
            self._current_claude_branch = None
            self.refresh_claude_branches()
    
    def on_refresh(self):
        """Manually refresh the project state."""
        if not self.project:
            return
        
        # Show we're refreshing
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("...")
        
        # Force a refresh
        self.refresh_ui()
        
        # Restore button
        self.btn_refresh.setText("↻")
        self.btn_refresh.setEnabled(True)
    
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
        
        # Clear previous output
        self.output_panel.clear()
        self.append_output(f"▶ Running {self.project.main_file}...\n\n")
        
        # Disable launch button while running
        self.btn_launch.setEnabled(False)
        self.btn_launch.setText("⏳ Running...")
        
        # Use QProcess for better Qt integration
        self.current_process = QProcess(self)
        self.current_process.setWorkingDirectory(str(self.project.path))
        
        # Connect signals
        self.current_process.readyReadStandardOutput.connect(self.on_stdout_ready)
        self.current_process.readyReadStandardError.connect(self.on_stderr_ready)
        self.current_process.finished.connect(self.on_process_finished)
        
        # Start the process
        self.current_process.start("python3", [self.project.main_file])
    
    def on_stdout_ready(self):
        """Handle stdout data from the running process."""
        if self.current_process:
            data = self.current_process.readAllStandardOutput()
            text = bytes(data).decode("utf-8", errors="replace")
            self.append_output(text)
    
    def on_stderr_ready(self):
        """Handle stderr data from the running process."""
        if self.current_process:
            data = self.current_process.readAllStandardError()
            text = bytes(data).decode("utf-8", errors="replace")
            self.append_output(text, is_error=True)
    
    def on_process_finished(self, exit_code, exit_status):
        """Handle process completion."""
        # Re-enable launch button
        self.btn_launch.setEnabled(True)
        self.btn_launch.setText("▶  Launch")
        
        # Show completion message
        if exit_code == 0:
            self.append_output(f"\n✓ Finished successfully")
        else:
            self.append_output(f"\n✗ Exited with code {exit_code}", is_error=True)
        
        self.current_process = None
    
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
        
        saved = self.project.save_version(message.strip())
        
        if saved:
            self.refresh_ui()
            self.project_changed.emit()
    
    def refresh_github_status(self):
        """Update the GitHub sync status display."""
        if not self.project:
            self.sync_status.setText("No project")
            self.btn_push.setEnabled(False)
            self.btn_pull.setEnabled(False)
            self.btn_connect.show()
            return
        
        if not self.project.has_remote():
            self.sync_status.setText("Not connected")
            self.sync_status.setStyleSheet("color: #888888;")
            self.btn_push.setEnabled(False)
            self.btn_pull.setEnabled(False)
            self.btn_connect.show()
            return
        
        # We have a remote - hide connect button, enable push/pull
        self.btn_connect.hide()
        self.btn_push.setEnabled(True)
        self.btn_pull.setEnabled(True)
        
        # Get sync status (this does a fetch, might be slow)
        status = self.project.get_sync_status()
        
        if status["status"] == "synced":
            self.sync_status.setText("✓ In sync")
            self.sync_status.setStyleSheet("color: #2ecc71;")
        elif status["status"] == "ahead":
            count = status["ahead"]
            self.sync_status.setText(f"⬆ {count} to push")
            self.sync_status.setStyleSheet("color: #4a9eff;")
        elif status["status"] == "behind":
            count = status["behind"]
            self.sync_status.setText(f"⬇ {count} to pull")
            self.sync_status.setStyleSheet("color: #f39c12;")
        elif status["status"] == "diverged":
            self.sync_status.setText("⚠ Diverged")
            self.sync_status.setStyleSheet("color: #e74c3c;")
        else:
            self.sync_status.setText("● Connected")
            self.sync_status.setStyleSheet("color: #888888;")
    
    def on_push(self):
        """Push to GitHub."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Disable buttons during operation
        self.btn_push.setEnabled(False)
        self.btn_pull.setEnabled(False)
        self.btn_push.setText("Pushing...")
        
        # Do the push
        success, message = self.project.push_to_github()
        
        # Re-enable buttons
        self.btn_push.setText("⬆ Push")
        self.btn_push.setEnabled(True)
        self.btn_pull.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Pushed!", message)
            self.refresh_github_status()
        else:
            QMessageBox.warning(self, "Push Failed", message)
    
    def on_pull(self):
        """Pull from GitHub."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Disable buttons during operation
        self.btn_push.setEnabled(False)
        self.btn_pull.setEnabled(False)
        self.btn_pull.setText("Pulling...")
        
        # Do the pull
        success, message = self.project.pull_from_github()
        
        # Re-enable buttons
        self.btn_pull.setText("⬇ Pull")
        self.btn_push.setEnabled(True)
        self.btn_pull.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Pulled!", message)
            self.refresh_ui()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Pull Failed", message)
    
    def on_connect_github(self):
        """Show dialog to connect project to GitHub."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Connect to GitHub")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Instructions
        instructions = QLabel(
            "Enter your GitHub repository URL.\n\n"
            "Example: https://github.com/username/repo-name\n\n"
            "Don't have a repo yet? Create one on GitHub first,\n"
            "then paste the URL here."
        )
        instructions.setStyleSheet("color: #666666; font-size: 13px;")
        layout.addWidget(instructions)
        
        # URL input
        self.github_url_input = QLineEdit()
        self.github_url_input.setPlaceholderText("https://github.com/username/repo-name")
        self.github_url_input.setStyleSheet("""
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
        
        # Pre-fill if we have a saved URL
        if self.project.github_repo:
            self.github_url_input.setText(self.project.github_repo)
        
        layout.addWidget(self.github_url_input)
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dialog.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_connect = QPushButton("Connect")
        btn_connect.setStyleSheet("""
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
        """)
        btn_connect.clicked.connect(lambda: self._do_connect_github(dialog))
        btn_layout.addWidget(btn_connect)
        
        layout.addWidget(btn_row)
        
        dialog.exec()
    
    def _do_connect_github(self, dialog):
        """Actually connect to GitHub after dialog input."""
        from PyQt6.QtWidgets import QMessageBox
        
        url = self.github_url_input.text().strip()
        
        if not url:
            QMessageBox.warning(dialog, "Missing URL", "Please enter a GitHub repository URL.")
            return
        
        # Basic URL validation
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
            self.refresh_github_status()
            QMessageBox.information(
                self,
                "Connected!",
                f"Your project is now connected to GitHub.\n\n"
                f"Use Push to upload your code, or Pull to get the latest changes."
            )
        else:
            QMessageBox.warning(dialog, "Connection Failed", message)
    
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
            
            #statusLabel {
                font-size: 13px;
                padding: 6px 12px;
                border-radius: 4px;
                background-color: #f1f1f1;
            }
            
            #btnRefresh {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 14px;
                min-width: 32px;
            }
            
            #btnRefresh:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            #btnRefresh:pressed {
                background-color: #e0e0e0;
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
            
            #githubLabel {
                color: #666666;
                font-size: 13px;
                font-weight: 500;
            }
            
            #syncStatus {
                font-size: 13px;
                font-weight: 500;
            }
            
            #githubButton {
                background-color: #f1f1f1;
                color: #333333;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #githubButton:hover {
                background-color: #e4e4e4;
                border-color: #999999;
            }
            
            #githubButton:pressed {
                background-color: #d4d4d4;
            }
            
            #githubButton:disabled {
                background-color: #f8f8f8;
                color: #aaaaaa;
                border-color: #dddddd;
            }
            
            #githubConnectButton {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                padding: 8px 16px;
                font-size: 13px;
                text-decoration: underline;
            }
            
            #githubConnectButton:hover {
                color: #3a8eef;
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
            
            #timelineEmpty {
                color: #666666;
                font-size: 13px;
                padding: 20px;
            }
        """)


class VersionItem(QFrame):
    """A single version in the timeline."""
    
    def __init__(self, message: str, date: str, hash: str, is_latest: bool = False):
        super().__init__()
        self.hash = hash
        
        self.setObjectName("versionItem")
        
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
