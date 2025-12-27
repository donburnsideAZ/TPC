"""
Clone from GitHub wizard for TPC.

The "Computer B" workflow - clone a repo from GitHub and import it into TPC
in one smooth step.

Flow:
1. Check GitHub connection (require setup if not connected)
2. Show dropdown of user's repos (or manual URL entry)
3. Pick where to put it
4. Clone + import automatically
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QWidget,
    QMessageBox, QComboBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core import Project, DEFAULT_PROJECTS_ROOT, register_project_path
from core.github import (
    has_github_credentials,
    get_github_username,
    clone_repository,
    extract_repo_name,
    normalize_github_url,
    fetch_user_repos
)
from ui.wizards.import_project import is_already_tpc_project


class RepoFetchWorker(QThread):
    """Background worker to fetch user's repositories."""
    
    finished = pyqtSignal(bool, str, list)  # success, message, repos
    
    def run(self):
        success, message, repos = fetch_user_repos()
        self.finished.emit(success, message, repos)


class CloneFromGitHubWizard(QDialog):
    """Wizard for cloning a GitHub repository into TPC."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.cloned_project: Project | None = None
        self.selected_location = DEFAULT_PROJECTS_ROOT
        self.repos: list[dict] = []
        self.fetch_worker: RepoFetchWorker | None = None
        self.use_manual_url = False
        
        self.setWindowTitle("Clone from GitHub")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.resize(650, 550)
        
        self.setup_ui()
        
        # Start loading repos if connected
        if has_github_credentials():
            self.load_repos()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Clone from GitHub")
        header.setObjectName("wizardHeader")
        layout.addWidget(header)
        
        # Check for credentials
        if not has_github_credentials():
            # Not connected - show setup message
            self.setup_not_connected_ui(layout)
        else:
            # Connected - show repo picker
            self.setup_connected_ui(layout)
        
        self.apply_styles()
    
    def setup_not_connected_ui(self, layout: QVBoxLayout):
        """Show UI when GitHub is not connected."""
        
        # Message
        message = QLabel(
            "You'll need to connect to GitHub first.\n\n"
            "This lets TPC access your repositories and clone them securely."
        )
        message.setObjectName("wizardSubheader")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        layout.addSpacing(20)
        
        # Big button to go to settings
        btn_settings = QPushButton("Open GitHub Settings")
        btn_settings.setObjectName("btnPrimary")
        btn_settings.setMinimumHeight(50)
        btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(btn_settings)
        
        layout.addStretch()
        
        # Cancel button
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addWidget(btn_row)
    
    def setup_connected_ui(self, layout: QVBoxLayout):
        """Show UI when GitHub is connected."""
        
        username = get_github_username()
        subheader = QLabel(f"Connected as {username}")
        subheader.setObjectName("wizardSubheader")
        layout.addWidget(subheader)
        
        # === REPO SELECTION ===
        repo_section = QWidget()
        repo_layout = QVBoxLayout(repo_section)
        repo_layout.setContentsMargins(0, 0, 0, 0)
        repo_layout.setSpacing(8)
        
        repo_label = QLabel("Select a repository")
        repo_label.setObjectName("fieldLabel")
        repo_layout.addWidget(repo_label)
        
        # Dropdown for repos
        self.repo_combo = QComboBox()
        self.repo_combo.setObjectName("repoCombo")
        self.repo_combo.setMinimumHeight(40)
        self.repo_combo.addItem("Loading repositories...")
        self.repo_combo.setEnabled(False)
        self.repo_combo.currentIndexChanged.connect(self.on_repo_selected)
        repo_layout.addWidget(self.repo_combo)
        
        # Manual URL toggle
        self.btn_manual = QPushButton("Or enter a URL manually...")
        self.btn_manual.setObjectName("btnLink")
        self.btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_manual.clicked.connect(self.toggle_manual_url)
        repo_layout.addWidget(self.btn_manual)
        
        # Manual URL input (hidden by default)
        self.manual_url_widget = QWidget()
        manual_layout = QVBoxLayout(self.manual_url_widget)
        manual_layout.setContentsMargins(0, 8, 0, 0)
        manual_layout.setSpacing(8)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("fieldInput")
        self.url_input.setPlaceholderText("https://github.com/username/repository")
        self.url_input.textChanged.connect(self.on_url_changed)
        manual_layout.addWidget(self.url_input)
        
        self.manual_url_widget.hide()
        repo_layout.addWidget(self.manual_url_widget)
        
        layout.addWidget(repo_section)
        
        # === PREVIEW ===
        self.preview_label = QLabel("")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)
        
        # === LOCATION ===
        loc_section = QWidget()
        loc_layout = QVBoxLayout(loc_section)
        loc_layout.setContentsMargins(0, 0, 0, 0)
        loc_layout.setSpacing(8)
        
        loc_label = QLabel("Clone to")
        loc_label.setObjectName("fieldLabel")
        loc_layout.addWidget(loc_label)
        
        loc_row = QWidget()
        loc_row_layout = QHBoxLayout(loc_row)
        loc_row_layout.setContentsMargins(0, 0, 0, 0)
        loc_row_layout.setSpacing(8)
        
        self.location_preview = QLabel(str(DEFAULT_PROJECTS_ROOT))
        self.location_preview.setObjectName("locationPreview")
        self.location_preview.setWordWrap(True)
        loc_row_layout.addWidget(self.location_preview, 1)
        
        btn_browse = QPushButton("Change")
        btn_browse.setObjectName("btnBrowse")
        btn_browse.clicked.connect(self.browse_location)
        loc_row_layout.addWidget(btn_browse)
        
        loc_layout.addWidget(loc_row)
        layout.addWidget(loc_section)
        
        layout.addStretch()
        
        # === STATUS ===
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        
        # === BUTTONS ===
        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(12)
        
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        self.btn_clone = QPushButton("Clone Repository")
        self.btn_clone.setObjectName("btnCreate")
        self.btn_clone.clicked.connect(self.clone_repository)
        self.btn_clone.setEnabled(False)
        btn_layout.addWidget(self.btn_clone)
        
        layout.addWidget(btn_row)
    
    def load_repos(self):
        """Fetch user's repositories in background."""
        self.fetch_worker = RepoFetchWorker()
        self.fetch_worker.finished.connect(self.on_repos_loaded)
        self.fetch_worker.start()
    
    def on_repos_loaded(self, success: bool, message: str, repos: list[dict]):
        """Handle repo list loaded."""
        self.fetch_worker = None
        
        if not success:
            self.repo_combo.clear()
            self.repo_combo.addItem(f"Error: {message}")
            return
        
        self.repos = repos
        self.repo_combo.clear()
        
        if not repos:
            self.repo_combo.addItem("No repositories found")
            return
        
        # Add repos to dropdown
        self.repo_combo.addItem("Select a repository...")
        
        for repo in repos:
            # Show name, with 🔒 for private repos
            display_name = repo["name"]
            if repo["private"]:
                display_name = f"🔒 {display_name}"
            
            # Add description if available
            if repo["description"]:
                desc = repo["description"][:50]
                if len(repo["description"]) > 50:
                    desc += "..."
                display_name = f"{display_name}  —  {desc}"
            
            self.repo_combo.addItem(display_name, repo)
        
        self.repo_combo.setEnabled(True)
    
    def on_repo_selected(self, index: int):
        """Handle repo selection from dropdown."""
        if index <= 0:
            self.preview_label.setText("")
            self.btn_clone.setEnabled(False)
            return
        
        repo = self.repo_combo.itemData(index)
        if not repo:
            return
        
        self.use_manual_url = False
        
        # Update preview
        repo_name = repo["name"]
        full_path = self.selected_location / repo_name
        self.preview_label.setText(f"Will create: {full_path}")
        self.preview_label.setStyleSheet("color: #27ae60; font-size: 13px;")
        self.btn_clone.setEnabled(True)
    
    def toggle_manual_url(self):
        """Toggle between dropdown and manual URL input."""
        if self.manual_url_widget.isHidden():
            self.manual_url_widget.show()
            self.btn_manual.setText("Use repository list")
            self.repo_combo.setEnabled(False)
            self.use_manual_url = True
            self.on_url_changed(self.url_input.text())
        else:
            self.manual_url_widget.hide()
            self.btn_manual.setText("Or enter a URL manually...")
            self.repo_combo.setEnabled(True)
            self.use_manual_url = False
            self.on_repo_selected(self.repo_combo.currentIndex())
    
    def on_url_changed(self, text: str):
        """Update preview when manual URL changes."""
        if not self.use_manual_url:
            return
        
        url = text.strip()
        
        if not url:
            self.preview_label.setText("")
            self.btn_clone.setEnabled(False)
            return
        
        repo_name = extract_repo_name(url)
        
        if repo_name:
            full_path = self.selected_location / repo_name
            self.preview_label.setText(f"Will create: {full_path}")
            self.preview_label.setStyleSheet("color: #27ae60; font-size: 13px;")
            self.btn_clone.setEnabled(True)
        else:
            self.preview_label.setText("Couldn't parse repository name from URL")
            self.preview_label.setStyleSheet("color: #e74c3c; font-size: 13px;")
            self.btn_clone.setEnabled(False)
    
    def browse_location(self):
        """Let user choose a different location."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Clone Location",
            str(self.selected_location),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.selected_location = Path(folder)
            self.location_preview.setText(str(self.selected_location))
            # Update preview
            if self.use_manual_url:
                self.on_url_changed(self.url_input.text())
            else:
                self.on_repo_selected(self.repo_combo.currentIndex())
    
    def open_settings(self):
        """Open settings dialog to GitHub tab."""
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.parent())
        dialog.exec()
        
        # Check if they connected
        if has_github_credentials():
            # Close this wizard so they can reopen with full UI
            QMessageBox.information(
                self,
                "Connected!",
                "Great! You're connected to GitHub.\n\n"
                "Click Clone from GitHub again to see your repositories."
            )
            self.reject()
    
    def clone_repository(self):
        """Clone the selected repository."""
        # Get URL from dropdown or manual input
        if self.use_manual_url:
            url = self.url_input.text().strip()
            if not url:
                QMessageBox.warning(self, "Missing URL", "Please enter a repository URL.")
                return
            url = normalize_github_url(url)
            repo_name = extract_repo_name(url)
        else:
            index = self.repo_combo.currentIndex()
            if index <= 0:
                QMessageBox.warning(self, "No Selection", "Please select a repository.")
                return
            
            repo = self.repo_combo.itemData(index)
            url = repo["clone_url"].replace(".git", "")  # Clean URL
            repo_name = repo["name"]
        
        if not repo_name:
            QMessageBox.warning(self, "Invalid URL", "Couldn't parse repository name.")
            return
        
        # Check if folder already exists
        target_path = self.selected_location / repo_name
        if target_path.exists():
            QMessageBox.warning(
                self,
                "Folder Exists",
                f"A folder named '{repo_name}' already exists at this location.\n\n"
                "Choose a different location or remove the existing folder."
            )
            return
        
        # Disable UI during clone
        self.btn_clone.setEnabled(False)
        self.btn_clone.setText("Cloning...")
        self.status_label.setText("Connecting to GitHub...")
        self.status_label.setStyleSheet("color: #666666; font-size: 13px;")
        
        # Force UI update
        QApplication.processEvents()
        
        def progress_callback(message):
            self.status_label.setText(message)
            QApplication.processEvents()
        
        # Do the clone
        success, message, project_path = clone_repository(
            url=url,
            destination=self.selected_location,
            progress_callback=progress_callback
        )
        
        if success and project_path:
            self.status_label.setText("Setting up TPC project...")
            QApplication.processEvents()
            
            try:
                # Check if this repo is already a TPC project (has .tpc or .ptc folder)
                if is_already_tpc_project(project_path):
                    # Just load it - Project.load handles .ptc → .tpc migration
                    self.cloned_project = Project.load(project_path)
                    # Register it so it shows in sidebar
                    register_project_path(project_path)
                else:
                    # Fresh repo, create TPC config
                    self.cloned_project = Project.import_existing(
                        folder=project_path,
                        name=repo_name,
                        main_file="main.py"  # Will be auto-detected if exists
                    )
                
                self.status_label.setText("Done!")
                self.status_label.setStyleSheet("color: #27ae60; font-size: 13px;")
                
                QMessageBox.information(
                    self,
                    "Success!",
                    f"Cloned and imported '{repo_name}'.\n\n"
                    "The project is now in TPC and connected to GitHub."
                )
                
                self.accept()
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Import Failed",
                    f"Cloned successfully, but couldn't set up TPC project:\n\n{e}"
                )
                # Still register it so user can see it
                register_project_path(project_path)
                self.accept()
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 13px;")
            
            QMessageBox.warning(self, "Clone Failed", message)
        
        self.btn_clone.setEnabled(True)
        self.btn_clone.setText("Clone Repository")
    
    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
            }
            
            #wizardHeader {
                color: #333333;
                font-size: 22px;
                font-weight: 600;
            }
            
            #wizardSubheader {
                color: #888888;
                font-size: 14px;
                margin-bottom: 8px;
            }
            
            #fieldLabel {
                color: #555555;
                font-size: 14px;
                font-weight: 500;
            }
            
            #fieldInput {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 10px 12px;
                color: #333333;
                font-size: 14px;
                min-height: 20px;
            }
            
            #fieldInput:focus {
                border-color: #4a9eff;
            }
            
            #repoCombo {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 8px 12px;
                color: #333333;
                font-size: 14px;
            }
            
            #repoCombo:focus {
                border-color: #4a9eff;
            }
            
            #repoCombo::drop-down {
                border: none;
                padding-right: 12px;
            }
            
            #repoCombo QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 6px;
                selection-background-color: #e8f4fd;
                selection-color: #333333;
            }
            
            #locationPreview {
                color: #666666;
                font-size: 13px;
                background-color: #f5f5f5;
                padding: 10px 12px;
                border-radius: 6px;
            }
            
            #previewLabel {
                font-size: 13px;
                padding: 4px 0;
            }
            
            #statusLabel {
                font-size: 13px;
                padding: 4px 0;
            }
            
            #btnBrowse {
                background-color: #e8e8e8;
                color: #555555;
                border: none;
                padding: 10px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            
            #btnBrowse:hover {
                background-color: #d8d8d8;
            }
            
            #btnLink {
                background-color: transparent;
                color: #4a9eff;
                border: none;
                padding: 4px 0;
                font-size: 13px;
                text-align: left;
            }
            
            #btnLink:hover {
                color: #3a8eef;
                text-decoration: underline;
            }
            
            #btnCancel {
                background-color: transparent;
                color: #666666;
                border: 1px solid #cccccc;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
            }
            
            #btnCancel:hover {
                background-color: #f0f0f0;
                color: #333333;
            }
            
            #btnCreate {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            
            #btnCreate:hover {
                background-color: #5aafff;
            }
            
            #btnCreate:pressed {
                background-color: #3a8eef;
            }
            
            #btnCreate:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            
            #btnPrimary {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 16px 32px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
            }
            
            #btnPrimary:hover {
                background-color: #5aafff;
            }
        """)
