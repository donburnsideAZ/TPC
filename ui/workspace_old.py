"""
Workspace widgets for TPC.

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
    import_clicked = pyqtSignal()
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
        
        btn_import = QPushButton("Import Existing Project")
        btn_import.setObjectName("welcomeButtonSecondary")
        btn_import.clicked.connect(self.import_clicked.emit)
        btn_layout.addWidget(btn_import)
        
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
        
        # === BACKUP SECTION (was GitHub section) ===
        backup_section = QWidget()
        backup_section.setMinimumWidth(450)
        backup_layout = QHBoxLayout(backup_section)
        backup_layout.setContentsMargins(0, 0, 0, 0)
        backup_layout.setSpacing(12)
        
        # Backup icon/label
        backup_label = QLabel("Backup:")
        backup_label.setObjectName("backupLabel")
        backup_layout.addWidget(backup_label)
        
        # Backup status indicator
        self.backup_status = QLabel("Not configured")
        self.backup_status.setObjectName("backupStatus")
        backup_layout.addWidget(self.backup_status)
        
        backup_layout.addSpacing(8)
        
        # Backup Now button
        self.btn_backup = QPushButton("⬆ Backup Now")
        self.btn_backup.setObjectName("backupButton")
        self.btn_backup.clicked.connect(self.on_backup)
        self.btn_backup.setEnabled(False)
        backup_layout.addWidget(self.btn_backup)
        
        backup_layout.addSpacing(8)
        
        # Set Up Backup button (shown when not connected)
        self.btn_setup_backup = QPushButton("Set Up Backup")
        self.btn_setup_backup.setObjectName("backupSetupButton")
        self.btn_setup_backup.clicked.connect(self.on_setup_backup)
        backup_layout.addWidget(self.btn_setup_backup)
        
        backup_layout.addStretch()
        
        layout.addWidget(backup_section)
        
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
    
    def refresh_ui(self):
        """Update all UI elements to reflect current project state.
        
        This is LOCAL ONLY - no network calls. Fast and snappy.
        """
        if not self.project:
            return
        
        # Update header
        self.project_name.setText(self.project.name)
        self.project_path.setText(str(self.project.path))
        
        # Update status - simple local check only
        if self.project.has_unsaved_changes:
            self.status_label.setText("● Unsaved changes")
            self.status_label.setStyleSheet("color: #ffa500;")
        else:
            self.status_label.setText("✓ All saved")
            self.status_label.setStyleSheet("color: #4a9eff;")
        
        # Update Launch button based on THIS project's running state
        if self._is_current_project_running():
            self.btn_launch.setEnabled(False)
            self.btn_launch.setText("⏳ Running...")
        else:
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("▶  Launch")
        
        # Check for branch issues (local check only)
        self.refresh_branch_warning()
        
        # Update backup status (local check only - no fetch)
        self.refresh_backup_status()
        
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
    
    def refresh_backup_status(self):
        """Update the backup status display.
        
        LOCAL ONLY - just checks if remote exists, no network fetch.
        """
        if not self.project:
            self.backup_status.setText("No project")
            self.btn_backup.setEnabled(False)
            self.btn_setup_backup.show()
            return
        
        if not self.project.has_remote():
            self.backup_status.setText("Not configured")
            self.backup_status.setStyleSheet("color: #888888;")
            self.btn_backup.setEnabled(False)
            self.btn_setup_backup.show()
            return
        
        # We have a remote - show backup available
        self.btn_setup_backup.hide()
        self.btn_backup.setEnabled(True)
        self.backup_status.setText("● Connected to GitHub")
        self.backup_status.setStyleSheet("color: #888888;")
    
    def on_backup(self):
        """Backup to GitHub (one-way push)."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        
        # Disable button during operation
        self.btn_backup.setEnabled(False)
        self.btn_backup.setText("Backing up...")
        
        # Do the push
        success, message = self.project.push_to_github()
        
        # Re-enable button
        self.btn_backup.setText("⬆ Backup Now")
        self.btn_backup.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Backed Up!", "Your project has been backed up to GitHub.")
        else:
            QMessageBox.warning(self, "Backup Failed", message)
    
    def on_setup_backup(self):
        """Show dialog to connect project to GitHub for backup."""
        if not self.project:
            return
        
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Set Up Backup")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Instructions
        instructions = QLabel(
            "Back up your project to GitHub for safekeeping.\n\n"
            "Enter your GitHub repository URL.\n"
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
        
        btn_connect = QPushButton("Set Up Backup")
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
        btn_connect.clicked.connect(lambda: self._do_setup_backup(dialog))
        btn_layout.addWidget(btn_connect)
        
        layout.addWidget(btn_row)
        
        dialog.exec()
    
    def _do_setup_backup(self, dialog):
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
            self.refresh_backup_status()
            QMessageBox.information(
                self,
                "Backup Configured!",
                f"Your project is now connected to GitHub.\n\n"
                f"Click 'Backup Now' anytime to save a copy to GitHub."
            )
        else:
            QMessageBox.warning(dialog, "Setup Failed", message)
    
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
        
        project_key = self._get_project_key()
        if not project_key:
            return
        
        # Clear previous output for this project
        self.output_panel.clear()
        self.append_output(f"▶ Running {self.project.main_file}...\n\n")
        
        # Disable launch button while running
        self.btn_launch.setEnabled(False)
        self.btn_launch.setText("⏳ Running...")
        
        # Use QProcess for better Qt integration
        process = QProcess(self)
        process.setWorkingDirectory(str(self.project.path))
        
        # Store which project this process belongs to
        process.setProperty("project_key", project_key)
        
        # Clean environment to avoid Qt library conflicts when launching PyQt apps
        env = process.processEnvironment()
        if env.isEmpty():
            from PyQt6.QtCore import QProcessEnvironment
            env = QProcessEnvironment.systemEnvironment()
        
        # Remove Qt-specific variables that can cause conflicts
        qt_vars_to_remove = [
            'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
            'QML_IMPORT_PATH', 'QML2_IMPORT_PATH',
            'QT_DEBUG_PLUGINS', 'QT_QPA_PLATFORM',
            'PYSIDE_DESIGNER_PLUGINS',
        ]
        for var in qt_vars_to_remove:
            env.remove(var)
        
        # Also remove any PYINSTALLER variables
        for key in list(env.keys()):
            if 'PYINSTALLER' in key or '_MEIPASS' in key:
                env.remove(key)
        
        process.setProcessEnvironment(env)
        
        # Connect signals
        process.readyReadStandardOutput.connect(lambda: self.on_stdout_ready(process))
        process.readyReadStandardError.connect(lambda: self.on_stderr_ready(process))
        process.finished.connect(lambda exit_code, exit_status: self.on_process_finished(process, exit_code, exit_status))
        
        # Track this process for this project
        self.running_processes[project_key] = process
        
        # Start the process
        process.start("python3", [self.project.main_file])
    
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
            
            #backupSetupButton {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                padding: 8px 16px;
                font-size: 13px;
                text-decoration: underline;
            }
            
            #backupSetupButton:hover {
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
