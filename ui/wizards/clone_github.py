"""
Clone from GitHub wizard for TPC.

The "Computer B" workflow - clone a repo from GitHub and import it into TPC
in one smooth step.

Flow:
1. Paste GitHub URL
2. Pick where to put it
3. Clone + import automatically
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QWidget,
    QMessageBox
)
from PyQt6.QtCore import Qt

from core.project import Project, DEFAULT_PROJECTS_ROOT, register_project_path
from core.github import (
    has_github_credentials,
    clone_repository,
    extract_repo_name,
    normalize_github_url
)


class CloneFromGitHubWizard(QDialog):
    """Wizard for cloning a GitHub repository into TPC."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.cloned_project: Project | None = None
        self.selected_location = DEFAULT_PROJECTS_ROOT
        
        self.setWindowTitle("Clone from GitHub")
        self.setModal(True)
        self.setMinimumSize(550, 450)
        self.resize(600, 480)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("Clone from GitHub")
        header.setObjectName("wizardHeader")
        layout.addWidget(header)
        
        subheader = QLabel(
            "Paste a GitHub repository URL and we'll clone it and set it up in TPC."
        )
        subheader.setObjectName("wizardSubheader")
        layout.addWidget(subheader)
        
        # Check for credentials
        if not has_github_credentials():
            warning = QWidget()
            warning_layout = QHBoxLayout(warning)
            warning_layout.setContentsMargins(12, 12, 12, 12)
            warning.setStyleSheet("""
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 8px;
            """)
            
            warning_text = QLabel(
                "You're not connected to GitHub yet. "
                "Go to Settings → GitHub to sign in first."
            )
            warning_text.setWordWrap(True)
            warning_text.setStyleSheet("color: #856404; font-size: 13px;")
            warning_layout.addWidget(warning_text)
            
            layout.addWidget(warning)
        
        # URL input
        url_section = QWidget()
        url_layout = QVBoxLayout(url_section)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_layout.setSpacing(8)
        
        url_label = QLabel("Repository URL")
        url_label.setObjectName("fieldLabel")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("fieldInput")
        self.url_input.setPlaceholderText("https://github.com/username/repository")
        self.url_input.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_input)
        
        layout.addWidget(url_section)
        
        # Preview
        self.preview_label = QLabel("")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setWordWrap(True)
        layout.addWidget(self.preview_label)
        
        # Location
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
        
        # Status label (for progress)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)
        
        # Buttons
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
        
        self.apply_styles()
    
    def on_url_changed(self, text: str):
        """Update preview when URL changes."""
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
            self.on_url_changed(self.url_input.text())  # Update preview
    
    def clone_repository(self):
        """Clone the repository and import into TPC."""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a GitHub repository URL.")
            return
        
        if not has_github_credentials():
            QMessageBox.warning(
                self,
                "Not Connected",
                "You need to connect to GitHub first.\n\n"
                "Go to Settings → GitHub to sign in."
            )
            return
        
        # Normalize the URL
        url = normalize_github_url(url)
        repo_name = extract_repo_name(url)
        
        if not repo_name:
            QMessageBox.warning(self, "Invalid URL", "Couldn't parse repository name from URL.")
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
        from PyQt6.QtWidgets import QApplication
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
                # Import into TPC
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
                font-size: 15px;
                min-height: 20px;
            }
            
            #fieldInput:focus {
                border-color: #4a9eff;
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
        """)
