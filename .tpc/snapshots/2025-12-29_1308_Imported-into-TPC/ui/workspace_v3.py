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
from PyQt6.QtCore import Qt, pyqtSignal, QProcess, QThread, QObject
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


class BackupWorker(QObject):
    """Worker to run backup in background thread."""
    finished = pyqtSignal(object)  # Emits BackupResult
    progress = pyqtSignal(str)
    
    def __init__(self, project_path, remote_url):
        super().__init__()
        self.project_path = project_path
        self.remote_url = remote_url
    
    def run(self):
        from core import backup_to_github
        result = backup_to_github(
            project_path=self.project_path,
            remote_url=self.remote_url,
            progress_callback=lambda msg: self.progress.emit(msg)
        )
        self.finished.emit(result)


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
        
        backup_label = QLabel("GitHub Backup:")
        backup_label.setObjectName("backupLabel")
        backup_layout.addWidget(backup_label)
        
        self.backup_status = QLabel("Not configured")
        self.backup_status.setObjectName("backupStatus")
        backup_layout.addWidget(self.backup_status)
        
        self.btn_backup = QPushButton("Set Up GitHub")
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
        
        # Launch button state and text based on project type
        if self.project.is_python_project():
            # Python project - run the script
            if self._is_current_project_running():
                self.btn_launch.setEnabled(False)
                self.btn_launch.setText("⏳ Running...")
            else:
                self.btn_launch.setEnabled(True)
                self.btn_launch.setText("▶  Launch")
            self.output_panel.setPlaceholderText("Click Launch to run your script...")
        else:
            # Folder project - open in Finder
            self.btn_launch.setEnabled(True)
            self.btn_launch.setText("📂 Open Folder")
            self.output_panel.setPlaceholderText("This is a folder project. Use 'Open Folder' to view files.")
        
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
            self.btn_backup.setText("Set Up GitHub")
    
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
        """Launch the project (run Python or open folder)."""
        if not self.project:
            return
        
        # For folder projects, just open in file manager
        if not self.project.is_python_project():
            self.project.open_in_finder()
            self.append_output("📂 Opened project folder in file manager\n")
            return
        
        # Python project - run the script
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
        
        # Clean environment for child process - remove Qt variables that could interfere
        # when launching other PyQt apps from a bundled TPC
        from PyQt6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        
        # Remove Qt variables that could cause library collisions
        for var in ['QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 
                    'QML_IMPORT_PATH', 'QML2_IMPORT_PATH',
                    'QT_DEBUG_PLUGINS', 'QT_QPA_PLATFORM',
                    'PYSIDE_DESIGNER_PLUGINS']:
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
        from core import has_github_credentials
        
        if not has_github_credentials():
            # Not connected - offer to connect
            reply = QMessageBox.question(
                self,
                "Connect to GitHub",
                "You need to connect to GitHub before setting up backup.\n\n"
                "Would you like to connect now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_github_settings()
                # After settings close, check if they connected and retry
                if has_github_credentials():
                    self.show_backup_setup()
            return
        
        # Connected - show repo picker dialog
        dialog = BackupSetupDialog(self, self.project.github_repo)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            url = dialog.get_selected_url()
            if url:
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
        """Perform the actual backup to GitHub in a background thread."""
        if not self.project or not self.project.github_repo:
            return
        
        from core import has_github_credentials
        
        # Check for at least one snapshot first
        if not self.project.has_snapshots:
            QMessageBox.warning(
                self,
                "Save a Version First",
                "You need to save at least one version before backing up to GitHub.\n\n"
                "Click 'Save Version' to create your first snapshot, then try backup again."
            )
            return
        
        # Check for GitHub credentials
        if not has_github_credentials():
            reply = QMessageBox.question(
                self,
                "GitHub Not Connected",
                "You need to connect to GitHub before backing up.\n\n"
                "Would you like to set up GitHub now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_github_settings()
            return
        
        # Check for secrets on first backup
        is_first_backup = self.project.get_last_backup_date() is None
        if is_first_backup:
            from core import scan_for_secrets
            
            findings = scan_for_secrets(
                self.project.path,
                self.project.ignore_patterns
            )
            
            if findings:
                # Show secrets warning dialog
                dialog = SecretsWarningDialog(self, findings, self.project)
                result = dialog.exec()
                
                if result == QDialog.DialogCode.Rejected:
                    # User cancelled
                    return
                
                # If user chose to add to ignore, the dialog already updated the project
                # Refresh the project config
                if dialog.added_to_ignore:
                    self.project.save_config()
        
        # Disable button during backup
        self.btn_backup.setEnabled(False)
        self.btn_backup.setText("Backing up...")
        self.backup_status.setText("Starting...")
        
        # Store project info for the callback (in case user switches projects)
        self._backup_project = self.project
        
        # Create worker and thread
        self._backup_thread = QThread()
        self._backup_worker = BackupWorker(
            self.project.path,
            self.project.github_repo
        )
        self._backup_worker.moveToThread(self._backup_thread)
        
        # Connect signals
        self._backup_thread.started.connect(self._backup_worker.run)
        self._backup_worker.progress.connect(self._on_backup_progress)
        self._backup_worker.finished.connect(self._on_backup_finished)
        self._backup_worker.finished.connect(self._backup_thread.quit)
        self._backup_worker.finished.connect(self._backup_worker.deleteLater)
        self._backup_thread.finished.connect(self._backup_thread.deleteLater)
        
        # Start the backup
        self._backup_thread.start()
    
    def _on_backup_progress(self, message: str):
        """Handle progress updates from backup worker."""
        self.backup_status.setText(message)
        # Force UI update
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def _on_backup_finished(self, result):
        """Handle backup completion."""
        # Re-enable button
        self.btn_backup.setEnabled(True)
        self.btn_backup.setText("Backup Now")
        
        if result.success:
            # Record the backup date
            from datetime import datetime
            if self._backup_project:
                self._backup_project.set_last_backup_date(datetime.now())
            self.refresh_backup_status()
            
            QMessageBox.information(
                self,
                "Backed Up!",
                f"{result.message}"
            )
        else:
            self.refresh_backup_status()
            QMessageBox.warning(
                self,
                "Backup Failed",
                result.message
            )
        
        # Clean up reference
        self._backup_project = None
    
    def show_github_settings(self):
        """Open the settings dialog to the GitHub tab."""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()
    
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


class SecretsWarningDialog(QDialog):
    """Dialog warning about potentially sensitive files before backup."""
    
    def __init__(self, parent=None, findings: list = None, project = None):
        super().__init__(parent)
        self.findings = findings or []
        self.project = project
        self.added_to_ignore = False
        
        self.setWindowTitle("Sensitive Files Detected")
        self.setModal(True)
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header with warning icon
        header = QLabel("⚠️ Potentially sensitive files found")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #e67e22;")
        layout.addWidget(header)
        
        # Explanation
        explanation = QLabel(
            "These files might contain API keys, passwords, or other secrets.\n"
            "Backing them up to GitHub could expose them publicly."
        )
        explanation.setStyleSheet("font-size: 13px; color: #666666;")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Findings list
        from PyQt6.QtWidgets import QScrollArea, QListWidget, QListWidgetItem
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #cccccc;
                border-radius: 6px;
                background-color: #f9f9f9;
            }
        """)
        
        findings_widget = QWidget()
        findings_layout = QVBoxLayout(findings_widget)
        findings_layout.setContentsMargins(12, 12, 12, 12)
        findings_layout.setSpacing(8)
        
        from core import get_severity_emoji
        
        for finding in self.findings:
            emoji = get_severity_emoji(finding.severity)
            
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(2)
            
            file_label = QLabel(f"{emoji} {finding.relative_path}")
            file_label.setStyleSheet("font-size: 13px; font-weight: 500; color: #333333;")
            item_layout.addWidget(file_label)
            
            reason_label = QLabel(finding.reason)
            reason_label.setStyleSheet("font-size: 12px; color: #666666; margin-left: 20px;")
            item_layout.addWidget(reason_label)
            
            findings_layout.addWidget(item_widget)
        
        findings_layout.addStretch()
        scroll.setWidget(findings_widget)
        layout.addWidget(scroll)
        
        # Legend
        legend = QLabel("🔴 High risk  🟡 Medium risk  🟢 Low risk")
        legend.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(legend)
        
        layout.addStretch()
        
        # Buttons
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        btn_cancel = QPushButton("Cancel Backup")
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
        
        btn_layout.addStretch()
        
        btn_ignore = QPushButton("Add to Ignore List")
        btn_ignore.setStyleSheet("""
            QPushButton {
                background-color: #f39c12; color: white;
                border: none; padding: 10px 20px;
                border-radius: 6px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background-color: #e67e22; }
        """)
        btn_ignore.clicked.connect(self.add_to_ignore)
        btn_layout.addWidget(btn_ignore)
        
        btn_continue = QPushButton("Backup Anyway")
        btn_continue.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white;
                border: none; padding: 10px 20px;
                border-radius: 6px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        btn_continue.clicked.connect(self.accept)
        btn_layout.addWidget(btn_continue)
        
        layout.addWidget(btn_row)
    
    def add_to_ignore(self):
        """Add all found files to the project's ignore list."""
        if not self.project:
            self.accept()
            return
        
        # Add each finding to ignore patterns
        for finding in self.findings:
            pattern = finding.relative_path
            if pattern not in self.project.ignore_patterns:
                self.project.ignore_patterns.append(pattern)
        
        self.added_to_ignore = True
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Added to Ignore",
            f"Added {len(self.findings)} file(s) to the ignore list.\n\n"
            "These files won't be included in backups or future scans."
        )
        
        self.accept()


class BackupSetupDialog(QDialog):
    """Dialog for selecting a GitHub repository for backup."""
    
    def __init__(self, parent=None, current_url: str = None):
        super().__init__(parent)
        self.current_url = current_url
        self.repos = []
        self.selected_url = None
        
        self.setWindowTitle("Set Up GitHub Backup")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.load_repos()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header = QLabel("Choose a repository for backup")
        header.setStyleSheet("font-size: 16px; font-weight: 600; color: #333333;")
        layout.addWidget(header)
        
        # Loading indicator
        self.loading_label = QLabel("Loading your repositories...")
        self.loading_label.setStyleSheet("color: #666666; font-size: 13px; padding: 20px;")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)
        
        # Repo dropdown (hidden until loaded)
        from PyQt6.QtWidgets import QComboBox
        self.repo_combo = QComboBox()
        self.repo_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:focus {
                border-color: #4a9eff;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cccccc;
                border-radius: 6px;
                selection-background-color: #e8f4fd;
                selection-color: #333333;
            }
        """)
        self.repo_combo.setPlaceholderText("Select a repository...")
        self.repo_combo.currentIndexChanged.connect(self.on_repo_selected)
        self.repo_combo.hide()
        layout.addWidget(self.repo_combo)
        
        # Manual URL option
        manual_section = QWidget()
        manual_layout = QVBoxLayout(manual_section)
        manual_layout.setContentsMargins(0, 8, 0, 0)
        manual_layout.setSpacing(8)
        
        manual_label = QLabel("Or enter a repository URL manually:")
        manual_label.setStyleSheet("color: #666666; font-size: 12px;")
        manual_layout.addWidget(manual_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://github.com/username/repo-name")
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 12px;
                border: 1px solid #cccccc;
                border-radius: 6px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #4a9eff;
            }
        """)
        if self.current_url:
            self.url_input.setText(self.current_url)
        manual_layout.addWidget(self.url_input)
        
        layout.addWidget(manual_section)
        
        # Create new repo link
        create_link = QLabel('<a href="https://github.com/new" style="color: #4a9eff;">Create a new repository on GitHub →</a>')
        create_link.setOpenExternalLinks(True)
        create_link.setStyleSheet("font-size: 13px; padding: 8px 0;")
        layout.addWidget(create_link)
        
        layout.addStretch()
        
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
        
        self.btn_select = QPushButton("Select Repository")
        self.btn_select.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff; color: white;
                border: none; padding: 10px 20px;
                border-radius: 6px; font-size: 13px; font-weight: 500;
            }
            QPushButton:hover { background-color: #5aafff; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.btn_select.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_select)
        
        layout.addWidget(btn_row)
    
    def load_repos(self):
        """Load the user's repositories from GitHub."""
        from core import fetch_user_repos
        
        success, message, repos = fetch_user_repos()
        
        if success and repos:
            self.repos = repos
            self.loading_label.hide()
            self.repo_combo.show()
            
            for repo in repos:
                # Format: repo-name (private indicator)
                display = repo["name"]
                if repo["private"]:
                    display += " 🔒"
                
                self.repo_combo.addItem(display, repo["clone_url"])
                
                # Pre-select if matches current URL
                if self.current_url and repo["clone_url"].rstrip(".git") in self.current_url:
                    self.repo_combo.setCurrentIndex(self.repo_combo.count() - 1)
        else:
            self.loading_label.setText(
                "Couldn't load repositories.\n\n"
                "You can still enter a URL manually below."
            )
            self.loading_label.setStyleSheet("color: #e67e22; font-size: 13px; padding: 20px;")
    
    def on_repo_selected(self, index):
        """When a repo is selected from dropdown, clear manual URL."""
        if index >= 0:
            self.url_input.clear()
    
    def get_selected_url(self) -> str:
        """Get the selected repository URL."""
        # Check manual input first
        manual_url = self.url_input.text().strip()
        if manual_url:
            return manual_url
        
        # Check dropdown selection
        if self.repo_combo.currentIndex() >= 0:
            return self.repo_combo.currentData()
        
        return None
    
    def accept(self):
        """Validate selection before accepting."""
        url = self.get_selected_url()
        
        if not url:
            QMessageBox.warning(
                self,
                "No Repository Selected",
                "Please select a repository from the list or enter a URL."
            )
            return
        
        # Basic validation
        if not ("github.com" in url):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "That doesn't look like a GitHub URL."
            )
            return
        
        self.selected_url = url
        super().accept()
