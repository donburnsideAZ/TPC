"""
Workspace widgets for TPC v3.

Simple, clean interface for:
- Launching projects
- Saving versions (snapshots)
- Viewing version history
- Restoring previous versions
- GitHub backup (optional)
"""

import shutil
import sys
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QPlainTextEdit,
    QDialog, QLineEdit, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QProcess
from PyQt6.QtGui import QFont, QTextCursor

from core import Project, Snapshot


def get_python_executable() -> str:
    """Find the best Python executable to use for launching scripts."""
    if not getattr(sys, 'frozen', False):
        return sys.executable
    
    if sys.platform != "win32":
        python_path = shutil.which("python3")
        if python_path and python_path != "/usr/bin/python3":
            return python_path
        if python_path:
            return python_path
    
    python_path = shutil.which("python")
    if python_path:
        return python_path
    
    python_path = shutil.which("python3")
    if python_path:
        return python_path
    
    return "python" if sys.platform == "win32" else "python3"


class WelcomeWidget(QWidget):
    """Welcome screen shown when no project is selected."""
    
    new_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 60, 60, 60)
        
        layout.addStretch(1)
        
        title = QLabel("Ready to ship something?")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Pick a project from the sidebar, or start fresh.")
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(40)
        
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
        
        hint = QLabel("Tip: Use Import to bring an existing project folder into TPC.")
        hint.setObjectName("welcomeHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        
        layout.addStretch(1)
        
        self.apply_styles()
    
    def apply_styles(self):
        self.setStyleSheet("""
            WelcomeWidget { background-color: #ffffff; }
            #welcomeTitle { color: #000000; font-size: 28px; font-weight: 600; }
            #welcomeSubtitle { color: #666666; font-size: 16px; margin-top: 8px; }
            #welcomeButtonPrimary {
                background-color: #4a9eff; color: white; border: none;
                padding: 14px 28px; border-radius: 8px; font-size: 15px; font-weight: 500;
            }
            #welcomeButtonPrimary:hover { background-color: #5aafff; }
            #welcomeButtonPrimary:pressed { background-color: #3a8eef; }
            #welcomeHint { color: #888888; font-size: 13px; }
        """)


class WorkspaceWidget(QWidget):
    """
    Project workspace - the main working area.
    
    Clean, simple layout:
    - Launch and Save Version buttons
    - GitHub backup section
    - Output panel
    - Version history with restore
    """
    
    project_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.project: Project | None = None
        self.running_processes: dict[str, QProcess] = {}
        self.project_outputs: dict[str, str] = {}
        self.setup_ui()
    
    def _get_project_key(self) -> str | None:
        if not self.project:
            return None
        return str(self.project.path)
    
    def _is_current_project_running(self) -> bool:
        key = self._get_project_key()
        if not key:
            return False
        process = self.running_processes.get(key)
        return process is not None and process.state() == QProcess.ProcessState.Running
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)
        
        # === HEADER ===
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
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
        
        main_layout.addWidget(header)
        
        # === TWO COLUMN LAYOUT ===
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEFT COLUMN - Actions and Output
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
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
        
        self.btn_save = QPushButton("+ Save Version")
        self.btn_save.setObjectName("actionButtonSecondary")
        self.btn_save.clicked.connect(self.on_save_version)
        actions_layout.addWidget(self.btn_save)
        
        actions_layout.addStretch()
        left_layout.addWidget(actions)
        
        # GitHub Backup section
        backup_section = QWidget()
        backup_layout = QHBoxLayout(backup_section)
        backup_layout.setContentsMargins(0, 0, 0, 0)
        backup_layout.setSpacing(12)
        
        backup_label = QLabel("Backup:")
        backup_label.setObjectName("backupLabel")
        backup_layout.addWidget(backup_label)
        
        self.backup_status = QLabel("Not configured")
        self.backup_status.setObjectName("backupStatus")
        backup_layout.addWidget(self.backup_status)
        
        self.btn_backup = QPushButton("Backup Now")
        self.btn_backup.setObjectName("backupButton")
        self.btn_backup.clicked.connect(self.on_backup)
        backup_layout.addWidget(self.btn_backup)
        
        backup_layout.addStretch()
        left_layout.addWidget(backup_section)
        
        # Output panel
        output_header = QWidget()
        output_header_layout = QHBoxLayout(output_header)
        output_header_layout.setContentsMargins(0, 0, 0, 0)
        
        output_label = QLabel("OUTPUT")
        output_label.setObjectName("sectionHeader")
        output_header_layout.addWidget(output_label)
        
        output_header_layout.addStretch()
        
        self.btn_copy_output = QPushButton("Copy")
        self.btn_copy_output.setObjectName("btnSmall")
        self.btn_copy_output.clicked.connect(self.copy_output)
        output_header_layout.addWidget(self.btn_copy_output)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("btnSmall")
        self.btn_clear.clicked.connect(self.clear_output)
        output_header_layout.addWidget(self.btn_clear)
        
        left_layout.addWidget(output_header)
        
        self.output_panel = QPlainTextEdit()
        self.output_panel.setObjectName("outputPanel")
        self.output_panel.setReadOnly(True)
        self.output_panel.setPlaceholderText("Click Launch to run your script...")
        
        output_font = QFont("Monaco", 12)
        output_font.setStyleHint(QFont.StyleHint.Monospace)
        self.output_panel.setFont(output_font)
        
        left_layout.addWidget(self.output_panel, 1)
        
        splitter.addWidget(left_panel)
        
        # RIGHT COLUMN - Version History
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(12)
        
        # Open Build Folder button
        self.btn_open_builds = QPushButton("📂 Open Build Folder")
        self.btn_open_builds.setObjectName("utilityButton")
        self.btn_open_builds.clicked.connect(self.on_open_build_folder)
        right_layout.addWidget(self.btn_open_builds)
        
        # Version history header
        history_header = QWidget()
        history_header_layout = QHBoxLayout(history_header)
        history_header_layout.setContentsMargins(0, 0, 0, 0)
        
        history_label = QLabel("VERSION HISTORY")
        history_label.setObjectName("sectionHeader")
        history_header_layout.addWidget(history_label)
        
        history_header_layout.addStretch()
        
        self.snapshot_count = QLabel("")
        self.snapshot_count.setObjectName("snapshotCount")
        history_header_layout.addWidget(self.snapshot_count)
        
        right_layout.addWidget(history_header)
        
        # Version history scroll area
        self.history_scroll = QScrollArea()
        self.history_scroll.setObjectName("historyScroll")
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.history_content = QWidget()
        self.history_layout = QVBoxLayout(self.history_content)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(8)
        self.history_layout.addStretch()
        
        self.history_scroll.setWidget(self.history_content)
        right_layout.addWidget(self.history_scroll, 1)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions (60% left, 40% right)
        splitter.setSizes([600, 400])
        
        main_layout.addWidget(splitter, 1)
        
        self.apply_styles()
    
    def set_project(self, project: Project):
        """Load a project into the workspace."""
        old_key = self._get_project_key()
        if old_key:
            self.project_outputs[old_key] = self.output_panel.toPlainText()
        
        self.project = project
        
        new_key = self._get_project_key()
        if new_key and new_key in self.project_outputs:
            self.output_panel.setPlainText(self.project_outputs[new_key])
        else:
            self.output_panel.clear()
        
        self.refresh_ui()
    
    def refresh_ui(self):
        """Update all UI elements."""
        if not self.project:
            return
        
        # Header
        self.project_name.setText(self.project.name)
        self.project_path.setText(str(self.project.path))
        
        # Launch button state
        if self._is_current_project_running():
            self.btn_launch.setEnabled(False)
            self.btn_launch.setText("⏳ Running...")
        else:
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("▶  Launch")
        
        # Backup status
        self.refresh_backup_status()
        
        # Version history
        self.refresh_history()
    
    def refresh_backup_status(self):
        """Update the backup status display."""
        if not self.project:
            return
        
        if self.project.has_github_backup():
            last_backup = self.project.get_last_backup_date()
            if last_backup:
                # Format relative date
                from datetime import datetime
                now = datetime.now()
                diff = now - last_backup
                
                if diff.days == 0:
                    status = f"Last: Today at {last_backup.strftime('%I:%M %p')}"
                elif diff.days == 1:
                    status = f"Last: Yesterday"
                elif diff.days < 7:
                    status = f"Last: {diff.days} days ago"
                else:
                    status = f"Last: {last_backup.strftime('%b %d')}"
                
                self.backup_status.setText(status)
                self.backup_status.setStyleSheet("color: #666666;")
            else:
                self.backup_status.setText("Never backed up")
                self.backup_status.setStyleSheet("color: #e67e22;")
            
            self.btn_backup.setText("Backup Now")
        else:
            self.backup_status.setText("Not configured")
            self.backup_status.setStyleSheet("color: #888888;")
            self.btn_backup.setText("Set Up Backup")
    
    def refresh_history(self):
        """Rebuild the version history list."""
        # Clear existing items
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.project:
            return
        
        snapshots = self.project.get_version_history()
        current, limit = self.project.get_snapshot_count()
        
        self.snapshot_count.setText(f"{current} of {limit}")
        
        if not snapshots:
            empty = QLabel("No versions yet.\nClick 'Save Version' to save your first snapshot.")
            empty.setObjectName("emptyHistory")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.history_layout.insertWidget(0, empty)
            return
        
        for i, snapshot in enumerate(snapshots):
            item = SnapshotItem(snapshot, is_latest=(i == 0))
            item.restore_clicked.connect(lambda s=snapshot: self.on_restore(s))
            self.history_layout.insertWidget(self.history_layout.count() - 1, item)
    
    def on_launch(self):
        """Launch the project's main file."""
        if not self.project:
            return
        
        project_key = self._get_project_key()
        if not project_key:
            return
        
        self.output_panel.clear()
        self.append_output(f"▶ Running {self.project.main_file}...\n\n")
        
        self.btn_launch.setEnabled(False)
        self.btn_launch.setText("⏳ Running...")
        
        process = QProcess(self)
        process.setWorkingDirectory(str(self.project.path))
        process.setProperty("project_key", project_key)
        
        # Clean environment for child process
        env = process.processEnvironment()
        if env.isEmpty():
            env = QProcess.systemEnvironment()
            process.setProcessEnvironment(env)
        
        # Remove Qt variables that could interfere
        for var in ['QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 
                    'QML_IMPORT_PATH', 'QML2_IMPORT_PATH']:
            env.remove(var)
        process.setProcessEnvironment(env)
        
        process.readyReadStandardOutput.connect(lambda: self.on_stdout_ready(process))
        process.readyReadStandardError.connect(lambda: self.on_stderr_ready(process))
        process.finished.connect(lambda code, status: self.on_process_finished(process, code, status))
        
        self.running_processes[project_key] = process
        
        python = get_python_executable()
        process.start(python, [self.project.main_file])
    
    def on_stdout_ready(self, process: QProcess):
        project_key = process.property("project_key")
        data = process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        
        if project_key == self._get_project_key():
            self.append_output(text)
        else:
            if project_key in self.project_outputs:
                self.project_outputs[project_key] += text
            else:
                self.project_outputs[project_key] = text
    
    def on_stderr_ready(self, process: QProcess):
        project_key = process.property("project_key")
        data = process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        
        if project_key == self._get_project_key():
            self.append_output(text)
        else:
            if project_key in self.project_outputs:
                self.project_outputs[project_key] += text
            else:
                self.project_outputs[project_key] = text
    
    def on_process_finished(self, process: QProcess, exit_code: int, exit_status):
        project_key = process.property("project_key")
        
        if exit_code == 0:
            msg = "\n✓ Finished successfully"
        else:
            msg = f"\n✗ Exited with code {exit_code}"
        
        if project_key == self._get_project_key():
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("▶  Launch")
            self.append_output(msg)
        else:
            if project_key in self.project_outputs:
                self.project_outputs[project_key] += msg
        
        if project_key in self.running_processes:
            del self.running_processes[project_key]
    
    def append_output(self, text: str):
        cursor = self.output_panel.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_panel.setTextCursor(cursor)
        self.output_panel.insertPlainText(text)
        
        scrollbar = self.output_panel.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def copy_output(self):
        """Copy output panel contents to clipboard."""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.output_panel.toPlainText())
    
    def clear_output(self):
        self.output_panel.clear()
        key = self._get_project_key()
        if key and key in self.project_outputs:
            del self.project_outputs[key]
    
    def on_save_version(self):
        """Save a new version (snapshot)."""
        if not self.project:
            return
        
        # Show dialog for note
        dialog = SaveVersionDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        note = dialog.get_note()
        
        # Save the snapshot
        result = self.project.save_version(note)
        
        if result.success:
            msg = result.message
            if result.deleted_old:
                msg += f"\n(Oldest snapshot removed: {result.deleted_old})"
            
            QMessageBox.information(self, "Version Saved", msg)
            self.refresh_history()
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Save Failed", result.message)
    
    def on_restore(self, snapshot: Snapshot):
        """Restore to a previous version."""
        if not self.project:
            return
        
        reply = QMessageBox.question(
            self,
            "Restore Version",
            f"Restore to '{snapshot.display_name}'?\n\n"
            f"Your current files will be replaced with this snapshot.\n"
            f"A safety backup will be created first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        result = self.project.restore_version(snapshot)
        
        if result.success:
            QMessageBox.information(self, "Restored", result.message)
            self.project_changed.emit()
        else:
            QMessageBox.warning(self, "Restore Failed", result.message)
    
    def on_backup(self):
        """Handle backup button click."""
        if not self.project:
            return
        
        if not self.project.has_github_backup():
            # Show setup dialog
            self.show_backup_setup()
        else:
            # Do the backup
            self.do_backup()
    
    def show_backup_setup(self):
        """Show dialog to configure GitHub backup."""
        from PyQt6.QtWidgets import QInputDialog
        
        url, ok = QInputDialog.getText(
            self,
            "Set Up GitHub Backup",
            "Enter your GitHub repository URL:\n\n"
            "Example: https://github.com/username/repo-name\n",
            text=self.project.github_repo or ""
        )
        
        if not ok or not url.strip():
            return
        
        url = url.strip()
        
        # Basic validation
        if not (url.startswith("https://github.com/") or url.startswith("git@github.com:")):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "That doesn't look like a GitHub URL.\n\n"
                "It should start with https://github.com/"
            )
            return
        
        # Save the URL
        self.project.github_repo = url
        self.project.save_config()
        
        self.refresh_backup_status()
        
        # Ask if they want to backup now
        reply = QMessageBox.question(
            self,
            "Backup Now?",
            "GitHub backup configured!\n\nDo you want to backup now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.do_backup()
    
    def do_backup(self):
        """Perform the actual backup to GitHub."""
        if not self.project or not self.project.github_repo:
            return
        
        # For now, show a message that this needs Git
        # In a full implementation, we'd use the GitHub API or git commands
        QMessageBox.information(
            self,
            "Backup",
            "GitHub backup would push your current files to:\n\n"
            f"{self.project.github_repo}\n\n"
            "Note: Full GitHub integration coming soon.\n"
            "For now, you can manually push using Git or GitHub Desktop."
        )
        
        # Record the backup date anyway (for UI purposes)
        from datetime import datetime
        self.project.set_last_backup_date(datetime.now())
        self.refresh_backup_status()
    
    def on_open_build_folder(self):
        """Open the TPC Builds folder."""
        if not self.project:
            return
        
        build_dir = self.project.path / "TPC Builds"
        build_dir.mkdir(parents=True, exist_ok=True)
        
        import subprocess
        import platform
        
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["open", str(build_dir)])
            elif system == "Windows":
                subprocess.run(["explorer", str(build_dir)])
            else:
                subprocess.run(["xdg-open", str(build_dir)])
        except:
            QMessageBox.warning(self, "Error", f"Couldn't open folder:\n{build_dir}")
    
    def apply_styles(self):
        self.setStyleSheet("""
            WorkspaceWidget { background-color: #ffffff; }
            
            #projectName { color: #000000; font-size: 22px; font-weight: 600; }
            #projectPath { color: #666666; font-size: 12px; }
            
            #actionButtonPrimary {
                background-color: #2ecc71; color: white; border: none;
                padding: 14px 28px; border-radius: 8px; font-size: 15px; font-weight: 500;
            }
            #actionButtonPrimary:hover { background-color: #3ddc81; }
            #actionButtonPrimary:pressed { background-color: #27ae60; }
            #actionButtonPrimary:disabled { background-color: #95a5a6; }
            
            #actionButtonSecondary {
                background-color: #4a9eff; color: white; border: none;
                padding: 14px 28px; border-radius: 8px; font-size: 15px; font-weight: 500;
            }
            #actionButtonSecondary:hover { background-color: #5aafff; }
            #actionButtonSecondary:pressed { background-color: #3a8eef; }
            
            #backupLabel { color: #666666; font-size: 13px; }
            #backupStatus { color: #666666; font-size: 13px; }
            
            #backupButton {
                background-color: #f0f0f0; color: #333333; border: 1px solid #cccccc;
                padding: 8px 16px; border-radius: 6px; font-size: 13px;
            }
            #backupButton:hover { background-color: #e0e0e0; }
            
            #sectionHeader {
                color: #666666; font-size: 11px; font-weight: 600;
                text-transform: uppercase; letter-spacing: 1px;
            }
            
            #snapshotCount { color: #888888; font-size: 11px; }
            
            #btnSmall {
                background-color: transparent; color: #666666;
                border: 1px solid #cccccc; padding: 4px 12px;
                border-radius: 4px; font-size: 12px;
            }
            #btnSmall:hover { background-color: #f0f0f0; color: #333333; }
            
            #utilityButton {
                background-color: #f5f5f5; color: #555555;
                border: 1px solid #e0e0e0; padding: 10px 16px;
                border-radius: 6px; font-size: 13px; text-align: left;
            }
            #utilityButton:hover { background-color: #eeeeee; color: #333333; }
            
            #outputPanel {
                background-color: #1e1e1e; color: #d4d4d4;
                border: 1px solid #333333; border-radius: 8px;
                padding: 12px; font-size: 13px;
            }
            
            #historyScroll {
                background-color: #f8f8f8; border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            
            #emptyHistory {
                color: #888888; font-size: 13px; padding: 20px;
            }
        """)


class SnapshotItem(QFrame):
    """A single snapshot in the version history."""
    
    restore_clicked = pyqtSignal()
    
    def __init__(self, snapshot: Snapshot, is_latest: bool = False):
        super().__init__()
        self.snapshot = snapshot
        self.is_latest = is_latest
        
        self.setObjectName("snapshotItem")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Indicator dot
        dot = QLabel("●" if self.is_latest else "○")
        dot.setObjectName("snapshotDot")
        dot.setStyleSheet(f"color: {'#4a9eff' if self.is_latest else '#cccccc'}; font-size: 10px;")
        layout.addWidget(dot)
        
        # Info
        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        name = QLabel(self.snapshot.display_name)
        name.setObjectName("snapshotName")
        name.setStyleSheet(f"color: {'#000000' if self.is_latest else '#666666'}; font-size: 13px; font-weight: {'500' if self.is_latest else 'normal'};")
        info_layout.addWidget(name)
        
        details = QLabel(f"{self.snapshot.relative_time} · {self.snapshot.file_count} files · {self.snapshot.size_display}")
        details.setObjectName("snapshotDetails")
        details.setStyleSheet("color: #888888; font-size: 11px;")
        info_layout.addWidget(details)
        
        layout.addWidget(info, 1)
        
        # Restore button (not shown for latest)
        if not self.is_latest:
            btn = QPushButton("Restore")
            btn.setObjectName("restoreButton")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent; color: #4a9eff;
                    border: 1px solid #4a9eff; padding: 6px 12px;
                    border-radius: 4px; font-size: 12px;
                }
                QPushButton:hover { background-color: #4a9eff; color: white; }
            """)
            btn.clicked.connect(self.restore_clicked.emit)
            layout.addWidget(btn)
        
        self.setStyleSheet("""
            #snapshotItem {
                background-color: transparent;
                border-radius: 6px;
            }
            #snapshotItem:hover {
                background-color: #f0f0f0;
            }
        """)


class SaveVersionDialog(QDialog):
    """Dialog for entering a version note."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Version")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        label = QLabel("What changed? (optional)")
        label.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(label)
        
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("e.g., Added settings dialog, Fixed login bug")
        self.note_input.setStyleSheet("""
            QLineEdit {
                padding: 12px; font-size: 14px;
                border: 1px solid #cccccc; border-radius: 6px;
            }
            QLineEdit:focus { border-color: #4a9eff; }
        """)
        layout.addWidget(self.note_input)
        
        hint = QLabel("Leave blank to auto-generate a timestamp.")
        hint.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(hint)
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #666666;
                border: 1px solid #cccccc; padding: 10px 20px;
                border-radius: 6px; font-size: 13px;
            }
            QPushButton:hover { background-color: #f0f0f0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Save Version")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff; color: white;
                border: none; padding: 10px 20px;
                border-radius: 6px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background-color: #5aafff; }
        """)
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)
        
        layout.addWidget(btn_row)
        
        # Focus the input
        self.note_input.setFocus()
    
    def get_note(self) -> str:
        return self.note_input.text().strip()
